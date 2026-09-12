import hashlib
import hmac
import html
import os
import time

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["THROTTLE_TABLE_NAME"])
secrets = boto3.client("secretsmanager")
_hmac_key = None

SIGNED_BODY = "/auth/signup:5:600"


def _key():
    global _hmac_key
    if _hmac_key is None:
        _hmac_key = secrets.get_secret_value(
            SecretId=os.environ["APPROVAL_HMAC_SECRET_ARN"]
        )["SecretString"].encode()
    return _hmac_key


def _expected(action, exp):
    msg = f"{action}:{exp}:{SIGNED_BODY}"
    return hmac.new(_key(), msg.encode(), hashlib.sha256).hexdigest()


def _page(status, message):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": f"<!doctype html><html><body><p>{html.escape(message)}</p></body></html>",
    }


def lambda_handler(event, context):
    qs = event.get("queryStringParameters") or {}
    action = qs.get("a", "")
    exp = qs.get("exp", "")
    sig = qs.get("sig", "")

    if action not in ("approve", "decline"):
        return _page(400, "Invalid action.")

    try:
        exp_i = int(exp)
    except ValueError:
        return _page(400, "Invalid token.")

    try:
        valid = hmac.compare_digest(sig, _expected(action, exp))
    except Exception:
        valid = False

    if not valid:
        return _page(403, "Invalid or tampered token.")

    if time.time() > exp_i:
        return _page(410, "This approval link has expired.")

    if action == "decline":
        print("AIOps approval declined")
        return _page(200, "Declined. No throttle written.")

    table.put_item(
        Item={
            "RuleName": "AI_EMERGENCY_SIGNUP_THROTTLE",
            "TargetEndpoint": "/auth/signup",
            "MaxRequestsPerMinute": 5,
            "ExpiresAt": int(time.time()) + 600,
        }
    )
    return _page(200, "Approved. /auth/signup throttled for 10 minutes.")
