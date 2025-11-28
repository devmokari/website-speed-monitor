import json
import os
import urllib.error
import urllib.parse
import urllib.request

INSIGHT_API_ENDPOINT = os.getenv("INSIGHT_API_ENDPOINT")


def fetch_insight(url: str) -> dict:
    if not INSIGHT_API_ENDPOINT:
        raise RuntimeError("INSIGHT_API_ENDPOINT environment variable is not set")
    encoded_url = urllib.parse.quote(url, safe="")
    request_url = f"{INSIGHT_API_ENDPOINT}?url={encoded_url}"
    try:
        with urllib.request.urlopen(request_url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            print(json.dumps({"url": url, "insight": payload}))  # logged for inspection
            return {"url": url, "insight": payload}
    except urllib.error.URLError as exc:  # pragma: no cover - network access
        detail = f"Failed to call insight API: {exc}"
        print(json.dumps({"url": url, "error": detail}))
        return {"url": url, "error": detail}


def lambda_handler(event, context):
    try:
        body = event.get("body") if isinstance(event, dict) else None
        parsed_body = json.loads(body or "{}")
        urls = parsed_body.get("urls", [])
        if not isinstance(urls, list):
            raise ValueError("`urls` must be a list")
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
