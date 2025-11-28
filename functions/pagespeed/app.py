import json
import os
import urllib.error
import urllib.parse
import urllib.request

TARGET_URL = "https://aoneauto.com.au/"
API_KEY = os.getenv("PAGESPEED_API_KEY")
REQUEST_TIMEOUT = int(os.getenv("PAGESPEED_TIMEOUT_SECONDS", "60"))
PAGE_SPEED_ENDPOINT = (
    "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}"
)


def fetch_performance(url: str, strategy: str) -> dict:
    encoded_url = urllib.parse.quote(url, safe="")
    request_url = PAGE_SPEED_ENDPOINT.format(url=encoded_url)
    if strategy:
        request_url = f"{request_url}&strategy={urllib.parse.quote(strategy.lower(), safe='')}"
    if API_KEY:
        request_url = f"{request_url}&key={API_KEY}"

    try:
        with urllib.request.urlopen(request_url, timeout=REQUEST_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:  # pragma: no cover - network access
        raise RuntimeError(f"Failed to call PageSpeed Insights: {exc}") from exc

    lighthouse = payload.get("lighthouseResult", {})
    categories = lighthouse.get("categories", {})
    performance = categories.get("performance", {})
    score = performance.get("score")
    if score is None:
        raise ValueError("Performance score missing from PageSpeed response")

    audits = lighthouse.get("audits", {})

    def metric(audit_key: str):
        audit = audits.get(audit_key, {})
        return audit.get("numericValue")

    metrics = {
        "firstContentfulPaintMs": metric("first-contentful-paint"),
        "largestContentfulPaintMs": metric("largest-contentful-paint"),
        "speedIndexMs": metric("speed-index"),
        "totalBlockingTimeMs": metric("total-blocking-time"),
        "timeToInteractiveMs": metric("interactive"),
        "cumulativeLayoutShift": metric("cumulative-layout-shift"),
    }

    return {"strategy": strategy.lower(), "score": score, "metrics": metrics}


def lambda_handler(event, context):
    try:
        mobile = fetch_performance(TARGET_URL, "mobile")
        desktop = fetch_performance(TARGET_URL, "desktop")
        body = {"url": TARGET_URL, "mobile": mobile, "desktop": desktop}
        status_code = 200
    except Exception as exc:  # pragma: no cover - defensive runtime handling
        body = {"message": "Failed to fetch PageSpeed Insights", "detail": str(exc)}
        status_code = 500

    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
