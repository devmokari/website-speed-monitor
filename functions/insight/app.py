import json
import os
from datetime import datetime, timezone
from typing import Dict, List
import urllib.error
import urllib.parse
import urllib.request

import boto3
from botocore.exceptions import BotoCoreError, ClientError

INSIGHT_API_ENDPOINT = os.getenv("INSIGHT_API_ENDPOINT")
INSIGHTS_TABLE_NAME = os.getenv("INSIGHTS_TABLE_NAME", "Insights")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(INSIGHTS_TABLE_NAME)


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_result(item: Dict) -> None:
    try:
        table.put_item(Item=item)
    except (BotoCoreError, ClientError) as exc:  # pragma: no cover - dependent on AWS
        # Log but do not fail the entire batch on DDB write errors
        print(json.dumps({"error": "Failed to write to DynamoDB", "detail": str(exc), "item": item}))


def fetch_insight(url: str) -> Dict:
    if not INSIGHT_API_ENDPOINT:
        raise RuntimeError("INSIGHT_API_ENDPOINT environment variable is not set")

    encoded_url = urllib.parse.quote(url, safe="")
    request_url = f"{INSIGHT_API_ENDPOINT}?url={encoded_url}"
    timestamp = iso_timestamp()

    try:
        with urllib.request.urlopen(request_url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            item = {
                "Url": url,
                "Timestamp": timestamp,
                "Status": "ok",
                "ResultJson": json.dumps(payload),
            }
            save_result(item)
            print(json.dumps({"url": url, "status": "ok"}))
            return {"url": url, "insight": payload, "status": "ok"}
    except urllib.error.URLError as exc:  # pragma: no cover - network access
        detail = f"Failed to call insight API: {exc}"
        item = {
            "Url": url,
            "Timestamp": timestamp,
            "Status": "error",
            "Error": detail,
        }
        save_result(item)
        print(json.dumps({"url": url, "status": "error", "detail": detail}))
        return {"url": url, "error": detail, "status": "error"}


def lambda_handler(event, context):
    try:
        print(json.dumps({"message": "Received event", "event": event}))
        parsed_event = event if isinstance(event, dict) else {}
        urls: List[str] = parsed_event.get("urls", [])
        if not isinstance(urls, list):
            raise ValueError("`urls` must be a list")
        print(json.dumps({"message": "Processing URLs", "count": len(urls)}))
        results = [fetch_insight(u) for u in urls]
        status_code = 200
        response_body = {"results": results}
    except Exception as exc:  # pragma: no cover - defensive runtime handling
        status_code = 400
        response_body = {"message": "Failed to process request", "detail": str(exc)}

    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response_body),
    }
