import hashlib
import hmac
import os
import time

import boto3

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime")
ses = boto3.client("ses")
secrets = boto3.client("secretsmanager")
MODEL_ID = os.environ["BEDROCK_MODEL_ID"]
_hmac_key = None

SIGNED_BODY = "/auth/signup:5:600"


def _key():
    global _hmac_key
    if _hmac_key is None:
        _hmac_key = secrets.get_secret_value(
            SecretId=os.environ["APPROVAL_HMAC_SECRET_ARN"]
        )["SecretString"].encode()
    return _hmac_key


def _link(action, exp):
    msg = f"{action}:{exp}:{SIGNED_BODY}"
    sig = hmac.new(_key(), msg.encode(), hashlib.sha256).hexdigest()
    base = os.environ["APPROVAL_URL"].rstrip("/")
    return f"{base}?a={action}&exp={exp}&sig={sig}"


def _send_approval_email():
    exp = int(time.time()) + 600
    sent_at = time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime())
    body = (
        "Issue: RDSConnectionStorm (active connections above threshold)\n"
        "Proposed: Throttle /auth/signup to 5 req/min for 10 min\n\n"
        f"Approve: {_link('approve', exp)}\n"
        f"Decline: {_link('decline', exp)}\n\n"
        "Expires in 10 minutes."
    )
    sent = ses.send_email(
        Source=os.environ["SES_FROM"],
        Destination={"ToAddresses": [os.environ["SES_TO"]]},
        Message={
            "Subject": {
                "Data": f"[AIOps] RDS Connection Storm — auth-service — {sent_at}"
            },
            "Body": {"Text": {"Data": body}},
        },
    )
    print("ses_message_id", sent["MessageId"])


def lambda_handler(event, context):
    record = event["Records"][0]["Sns"]
    alert_text = record["Message"]
    alert_subject = record.get("Subject", "")

    runbook = s3.get_object(
        Bucket=os.environ["RUNBOOK_BUCKET"],
        Key="rds_connection_storm.md",
    )["Body"].read().decode()

    response = bedrock.converse(
        modelId=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": (
                            "You are an SRE remediation engine. Given this alert and runbook, "
                            "reply with exactly one word: THROTTLE if the runbook's remediation "
                            "applies, or IGNORE if it does not.\n\n"
                            f"ALERT SUBJECT: {alert_subject}\n"
                            f"ALERT:\n{alert_text}\n\nRUNBOOK:\n{runbook}"
                        )
                    }
                ],
            }
        ],
    )
    decision = response["output"]["message"]["content"][0]["text"].strip().upper()

    if "THROTTLE" in decision:
        _send_approval_email()
        return {"statusCode": 200, "body": "Approval email sent."}

    return {"statusCode": 200, "body": f"No action taken (model said: {decision})."}
