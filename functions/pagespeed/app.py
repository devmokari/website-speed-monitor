import json
import urllib.error
import urllib.parse
import urllib.request

TARGET_URL = "https://example.com"
PAGE_SPEED_ENDPOINT = (
    "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}"
)


def fetch_performance_score(url: str) -> float:
    encoded_url = urllib.parse.quote(url, safe="")
    request_url = PAGE_SPEED_ENDPOINT.format(url=encoded_url)

    try:
        with urllib.request.urlopen(request_url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:  # pragma: no cover - network access
        raise RuntimeError(f"Failed to call PageSpeed Insights: {exc}") from exc

    categories = payload.get("lighthouseResult", {}).get("categories", {})
    performance = categories.get("performance", {})
    score = performance.get("score")
    if score is None:
        raise ValueError("Performance score missing from PageSpeed response")

    return score


def lambda_handler(event, context):
    try:
        score = fetch_performance_score(TARGET_URL)
        body = {"url": TARGET_URL, "performanceScore": score}
        status_code = 200
    except Exception as exc:  # pragma: no cover - defensive runtime handling
        body = {"message": "Failed to fetch PageSpeed Insights", "detail": str(exc)}
        status_code = 500

    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
