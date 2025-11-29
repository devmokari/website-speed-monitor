import json
import boto3
from urllib.parse import parse_qs
import os

table = boto3.resource("dynamodb").Table("Insights")

# Load HTML once during cold start
BASE_DIR = os.path.dirname(__file__)
with open(os.path.join(BASE_DIR, "templates/index.html"), "r") as f:
    HTML_PAGE = f.read()

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
            ExpressionAttributeNames={"#u": "Url"}
        )
        urls = sorted({item["Url"] for item in resp.get("Items", [])})
        return json_ok({"urls": urls})

    # 3. Data for selected URL
    if path == "/data":
        params = event.get("queryStringParameters") or {}
        url = params.get("url")
        resp = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("Url").eq(url)
        )
        return json_ok({"items": resp.get("Items", [])})

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
