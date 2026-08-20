"""GitOps-safe emergency throttle: cache-aside poller + per-pod sliding window.

The AIOps remediation Lambda writes a TTL'd rate-limit flag for an endpoint
(e.g. ``/auth/signup``) into the ``ai-throttle-config`` DynamoDB table. Every
auth pod polls that table into local memory every 10 seconds; the HTTP
middleware (see ``auth/main.py``) then enforces a per-pod sliding-window limit
on any path that has an active flag.

Design notes (see "AIOps & Load Test v3", Section 5):
  * Polling (not per-request reads) avoids turning an RDS storm into a
    DynamoDB read storm — one ``Scan`` per pod per 10s.
  * boto3 is blocking, so the scan runs via ``asyncio.to_thread`` and never
    freezes the event loop.
  * Nothing here mutates AWS or ArgoCD state, so there is no GitOps drift and
    the item's TTL lifts the throttle automatically.
  * Cross-pod precision is irrelevant — we only need aggregate load to collapse
    below the storm threshold.
"""

import asyncio
import logging
import os
import time
from collections import deque

import boto3
from app.shared.config import settings

logger = logging.getLogger("auth.throttle")

THROTTLE_TABLE_NAME = os.environ.get("THROTTLE_TABLE_NAME", "ai-throttle-config")
POLL_INTERVAL_SECONDS = 10


def throttle_enabled() -> bool:
    """Run the poller in AWS by default, stay quiet locally.

    Explicit override: set ``THROTTLE_ENABLED=true|false``. Otherwise the poller
    is enabled only when DB credentials come from Secrets Manager (i.e. in the
    cluster with Pod Identity), so a local ``docker compose`` run — where there
    is no DynamoDB — doesn't log scan errors every 10 seconds.
    """
    flag = os.environ.get("THROTTLE_ENABLED")
    if flag is not None:
        return flag.lower() in ("1", "true", "yes", "on")
    return os.environ.get("DB_CREDENTIALS_SOURCE", "env") == "secretsmanager"


class ThrottleManager:
    def __init__(self) -> None:
        # endpoint path -> max requests per minute (refreshed by the poller)
        self.active_throttles: dict[str, int] = {}
        self.table_name = THROTTLE_TABLE_NAME
        self._table = None
        self._recent_hits: dict[str, deque] = {}

    def _get_table(self):
        # Lazily build the resource so import never requires AWS connectivity.
        if self._table is None:
            resource = boto3.resource(
                "dynamodb",
                region_name=settings.AWS_DEFAULT_REGION,
                endpoint_url=settings.AWS_ENDPOINT_URL,  # None in AWS; LocalStack URL locally
            )
            self._table = resource.Table(self.table_name)
        return self._table

    async def poll_forever(self, stop_event: asyncio.Event) -> None:
        """Refresh ``active_throttles`` from DynamoDB every ``POLL_INTERVAL_SECONDS``."""
        while not stop_event.is_set():
            try:
                response = await asyncio.to_thread(self._get_table().scan)
                now = int(time.time())
                self.active_throttles = {
                    item["TargetEndpoint"]: int(item["MaxRequestsPerMinute"])
                    for item in response.get("Items", [])
                    # Honour the TTL precisely at the app layer — DynamoDB TTL
                    # deletion can lag by up to 48h, so we filter on ExpiresAt too.
                    if int(item.get("ExpiresAt", 0)) > now
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("Throttle poll failed: %s", exc)
            # Cancellable sleep that also wakes immediately on shutdown.
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=POLL_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass

    def is_blocked(self, path: str) -> bool:
        """Per-pod sliding-window check for ``path``; ``False`` when not throttled."""
        limit = self.active_throttles.get(path)
        if limit is None:
            return False
        hits = self._recent_hits.setdefault(path, deque())
        now = time.time()
        while hits and hits[0] < now - 60:
            hits.popleft()
        if len(hits) >= limit:
            return True
        hits.append(now)
        return False


# Single per-process instance shared by the lifespan poller and the middleware.
manager = ThrottleManager()
