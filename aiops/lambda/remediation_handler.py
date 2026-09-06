import os
import time

import boto3

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["THROTTLE_TABLE_NAME"])
MODEL_ID = os.environ["BEDROCK_MODEL_ID"]


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
        table.put_item(
            Item={
                "RuleName": "AI_EMERGENCY_SIGNUP_THROTTLE",
                "TargetEndpoint": "/auth/signup",
                "MaxRequestsPerMinute": 5,
                "ExpiresAt": int(time.time()) + 600,
            }
        )
        return {"statusCode": 200, "body": "Emergency application-level throttle applied."}

    return {"statusCode": 200, "body": f"No action taken (model said: {decision})."}
