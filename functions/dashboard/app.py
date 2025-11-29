import base64
import json
import os
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key
from flask import Flask, abort, render_template, request

app = Flask(__name__, template_folder="templates")

INSIGHTS_TABLE_NAME = os.getenv("INSIGHTS_TABLE_NAME", "Insights")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(INSIGHTS_TABLE_NAME)


def _scan_urls() -> List[str]:
    urls = set()
    last_evaluated_key: Optional[Dict[str, Any]] = None
    while True:
        kwargs = {"ProjectionExpression": "Url"}
        if last_evaluated_key:
            kwargs["ExclusiveStartKey"] = last_evaluated_key
        resp = table.scan(**kwargs)
        for item in resp.get("Items", []):
            url = item.get("Url")
            if url:
                urls.add(url)
        last_evaluated_key = resp.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break
    return sorted(urls)


def _parse_mobile_score(record: Dict[str, Any]) -> Optional[float]:
    raw = record.get("ResultJson")
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    mobile = None
    if isinstance(payload, dict):
        mobile = payload.get("mobile") or payload.get("insight", {}).get("mobile", {})
    if isinstance(mobile, dict):
        score = mobile.get("score")
        try:
            return float(score) if score is not None else None
        except (TypeError, ValueError):
            return None
    return None


def _query_records(url: str) -> List[Dict[str, Any]]:
    resp = table.query(
        KeyConditionExpression=Key("Url").eq(url),
        ScanIndexForward=False,  # latest first
    )
    records = resp.get("Items", [])
    for rec in records:
        rec["MobileScore"] = _parse_mobile_score(rec)
    return records


@app.route("/")
def index():
    print(json.dumps({"message": "Rendering index"}))
    urls = _scan_urls()
    return render_template("index.html", urls=urls)


@app.route("/url")
def url_details():
    target_url = request.args.get("url")
    if not target_url:
        abort(400, description="Missing url parameter")
    print(json.dumps({"message": "Rendering details", "url": target_url}))
    records = _query_records(target_url)
    return render_template("details.html", url=target_url, records=records)


@app.route("/health")
def health():
    return {"status": "ok"}


def lambda_handler(event, context):
    """
    Minimal adapter from API Gateway/Lambda proxy events to Flask without awsgi.
    """
    try:
        print(json.dumps({"message": "Received event", "event": event}))
        raw_path = event.get("rawPath") or event.get("path") or "/"
        raw_query = event.get("rawQueryString") or ""
        http_method = (
            event.get("requestContext", {}).get("http", {}).get("method")
            or event.get("httpMethod")
            or "GET"
        )
        headers = event.get("headers") or {}
        body = event.get("body") or ""
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body)

        path_with_qs = raw_path
        if raw_query:
            path_with_qs = f"{raw_path}?{raw_query}"

        with app.test_request_context(
            path=path_with_qs,
            method=http_method,
            headers=headers,
            data=body,
        ):
            resp = app.full_dispatch_request()

        return {
            "statusCode": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.get_data(as_text=True),
        }
    except Exception as exc:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/plain"},
            "body": f"Error: {exc}",
        }
