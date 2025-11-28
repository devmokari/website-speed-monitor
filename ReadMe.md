# Website Speed Monitor (MVP)

This initial version deploys a single AWS Lambda function that calls the Google PageSpeed Insights API for one hard-coded URL and exposes the result via a simple `GET /run` endpoint.

## Running locally

1. Build the SAM application:

   ```bash
   make build
   ```

2. Start the local API Gateway emulator:

   ```bash
   make local
   ```

3. Call the endpoint from a separate terminal:

   ```bash
   curl http://127.0.0.1:3000/run
   ```

## Deploying

Deploy with guided prompts to configure the stack name, region, and other required settings:

```bash
make deploy
```

## API

- `GET /run`: Returns JSON containing the hard-coded URL and its current PageSpeed performance score.
