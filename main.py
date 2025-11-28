import json
from functions.pagespeed.app import lambda_handler


def main():
    # Read URL from url.txt; if missing/empty, let the handler fall back to DEFAULT_URL.
    try:
        with open("url.txt", "r", encoding="utf-8") as f:
            url = f.read().strip() or None
    except FileNotFoundError:
        url = None
    event = {}
    if url:
        event["queryStringParameters"] = {"url": url}

    response = lambda_handler(event, None)
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
