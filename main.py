import json

from functions.pagespeed.app import lambda_handler


def main():
    # Invoke the Lambda handler locally without SAM/Docker.
    response = lambda_handler({"path": "/run"}, None)
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
