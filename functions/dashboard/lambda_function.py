import json
import os
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key

table = boto3.resource("dynamodb").Table("Insights")

# Load HTML once during cold start
BASE_DIR = os.path.dirname(__file__)
with open(os.path.join(BASE_DIR, "templates/index.html"), "r") as f:
    HTML_PAGE = f.read()


def _parse_record(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return parsed mobile/desktop scores (0-100) for a successful record."""
    if item.get("Status") != "ok":
        return None
    raw = item.get("ResultJson")
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    ts = item.get("Timestamp")
    mobile_score = None
    desktop_score = None

    if isinstance(payload, dict):
        mobile = payload.get("mobile", {})
        desktop = payload.get("desktop", {})
        if isinstance(mobile, dict) and mobile.get("score") is not None:
            mobile_score = float(mobile.get("score")) * 100
        if isinstance(desktop, dict) and desktop.get("score") is not None:
            desktop_score = float(desktop.get("score")) * 100

    return {"timestamp": ts, "mobile": mobile_score, "desktop": desktop_score}


def lambda_handler(event, context):
    path = event.get("rawPath", "/")

    # 1. Root HTML page
    if path in ("/", ""):
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": HTML_PAGE,
        }

    # 2. URL list (for dropdown)
    if path == "/urls":
        resp = table.scan(
            ProjectionExpression="#u",
            ExpressionAttributeNames={"#u": "Url"},
        )
        urls = sorted({item["Url"] for item in resp.get("Items", [])})
        return json_ok({"urls": urls})

    # 3. Data for selected URL (mobile/desktop series)
    if path == "/data":
        params = event.get("queryStringParameters") or {}
        url = params.get("url")
        if not url:
            return json_error("Missing url parameter")

        resp = table.query(
            KeyConditionExpression=Key("Url").eq(url),
            ScanIndexForward=True,  # oldest to newest
        )

        mobile_points: List[Dict[str, Any]] = []
        desktop_points: List[Dict[str, Any]] = []
        for item in resp.get("Items", []):
            parsed = _parse_record(item)
            if not parsed:
                continue
            ts = parsed["timestamp"]
            if parsed["mobile"] is not None:
                mobile_points.append({"t": ts, "y": parsed["mobile"]})
            if parsed["desktop"] is not None:
                desktop_points.append({"t": ts, "y": parsed["desktop"]})

        return json_ok(
            {
                "url": url,
                "mobile": mobile_points,
                "desktop": desktop_points,
            }
        )

    return json_error("Invalid route")


def json_ok(body):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def json_error(msg):
    return {
        "statusCode": 400,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": msg}),
    }
