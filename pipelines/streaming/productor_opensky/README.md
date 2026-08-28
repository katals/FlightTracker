# OpenSky Producer

Cloud Run service that polls the OpenSky states endpoint and publishes each
state vector to Pub/Sub using the `opensky.state.v1` contract.

## Required environment variables

- `GCP_PROJECT_ID`
- `PUBSUB_TOPIC` (default: `opensky-states-v1`)

## Optional environment variables

- `OPENSKY_URL`
- `OPENSKY_USERNAME`
- `OPENSKY_PASSWORD`
- `REQUEST_TIMEOUT_SEC`

## HTTP contract

- `GET /health`
- `GET /`
- `POST /`

The root endpoint fetches a snapshot from OpenSky and publishes one Pub/Sub
message per normalized aircraft state.
