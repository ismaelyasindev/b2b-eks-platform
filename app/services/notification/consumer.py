"""SQS Worker engine.

A non-blocking async drain loop:
  * blocking boto3 long-poll calls are offloaded with `asyncio.to_thread`
  * each message is idempotency-checked against notification_schema.delivery_logs
  * the DLQ sentinel (order_id == 999) raises, leaving the message un-deleted so
    SQS redrives it to the Dead Letter Queue after maxReceiveCount is exceeded
"""

import asyncio
import json
import logging

import boto3
from app.services.notification.models import DeliveryLog
from app.shared.config import settings
from app.shared.db import SessionLocal
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select

logger = logging.getLogger("notification.consumer")

DLQ_SENTINEL_ORDER_ID = 999


def _sqs_client():
    return boto3.client(
        "sqs",
        region_name=settings.AWS_DEFAULT_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL,
    )


def _ensure_queue(sqs) -> str:
    return sqs.create_queue(QueueName=settings.SQS_QUEUE_NAME)["QueueUrl"]


async def _already_processed(message_id: str) -> bool:
    async with SessionLocal() as db:
        existing = (
            await db.execute(select(DeliveryLog).where(DeliveryLog.message_id == message_id))
        ).scalar_one_or_none()
        return existing is not None


async def _record_delivery(message_id: str, body: dict) -> None:
    async with SessionLocal() as db:
        db.add(
            DeliveryLog(
                message_id=message_id,
                event_type=body.get("event_type", "unknown"),
                order_id=body.get("order_id"),
                payload=json.dumps(body),
                status="SENT",
            )
        )
        await db.commit()


async def process_message(message: dict) -> None:
    """Process one SQS message. Raises on the DLQ sentinel so it is retried."""
    message_id = message.get("MessageId", "")
    raw_body = message.get("Body", "{}")
    try:
        body = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Discarding non-JSON message %s", message_id)
        return

    # Idempotency guard (at-least-once delivery -> exactly-once side effects).
    if message_id and await _already_processed(message_id):
        logger.info("Skipping duplicate message %s", message_id)
        return

    order_id = body.get("order_id")
    if order_id == DLQ_SENTINEL_ORDER_ID:
        raise RuntimeError("Simulated notification failure for order 999")

    await _record_delivery(message_id, body)
    logger.info("Delivered notification for order_id=%s (msg %s)", order_id, message_id)


async def consume_forever(stop_event: asyncio.Event) -> None:
    """Long-poll the queue until `stop_event` is set."""
    try:
        sqs = _sqs_client()
        queue_url = await asyncio.to_thread(_ensure_queue, sqs)
    except (BotoCoreError, ClientError, KeyError) as exc:
        logger.warning("SQS unavailable; consumer idle: %s", exc)
        return

    logger.info("Notification consumer polling %s", queue_url)
    while not stop_event.is_set():
        try:
            response = await asyncio.to_thread(
                sqs.receive_message,
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=5,
            )
            messages = response.get("Messages", [])
            for message in messages:
                try:
                    await process_message(message)
                except Exception as exc:  # noqa: BLE001 - leave for retry/DLQ
                    logger.error("Processing failed (left for retry/DLQ): %s", exc)
                    continue
                await asyncio.to_thread(
                    sqs.delete_message,
                    QueueUrl=queue_url,
                    ReceiptHandle=message["ReceiptHandle"],
                )
        except (BotoCoreError, ClientError) as exc:
            logger.error("SQS receive error: %s", exc)
            await asyncio.sleep(2)
