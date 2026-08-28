import hashlib
import json
import os
import time
from typing import Any

import requests
from flask import Flask, jsonify, request
from google.cloud import pubsub_v1


app = Flask(__name__)

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
PUBSUB_TOPIC = os.environ.get("PUBSUB_TOPIC", "opensky-states-v1")
OPENSKY_URL = os.environ.get("OPENSKY_URL", "https://opensky-network.org/api/states/all")
OPENSKY_USERNAME = os.environ.get("OPENSKY_USERNAME")
OPENSKY_PASSWORD = os.environ.get("OPENSKY_PASSWORD")
REQUEST_TIMEOUT_SEC = float(os.environ.get("REQUEST_TIMEOUT_SEC", "30"))
SCHEMA_VERSION = "opensky.state.v1"

publisher = pubsub_v1.PublisherClient()


def _topic_path() -> str:
    if not PROJECT_ID:
        raise ValueError("GCP_PROJECT_ID is required")
    return publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)


def _build_event_id(observed_at: int | None, icao24: str, last_contact: int | None) -> str:
    key = f"{observed_at}|{icao24}|{last_contact or ''}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _normalize_state_vector(observed_at: int | None, state: list[Any]) -> dict[str, Any] | None:
    if not state or not state[0]:
        return None

    icao24 = str(state[0]).strip().lower()
    callsign = (state[1] or "").strip()
    last_contact = state[4]

    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": _build_event_id(observed_at, icao24, last_contact),
        "observed_at": observed_at,
        "icao24": icao24,
        "callsign": callsign,
        "origin_country": state[2],
        "longitude": state[5],
        "latitude": state[6],
        "baro_altitude": state[7],
        "on_ground": state[8],
        "velocity": state[9],
        "heading": state[10],
        "vertical_rate": state[11],
        "geo_altitude": state[13],
        "squawk": state[14],
        "spi": state[15],
        "position_source": state[16],
        "category": state[17] if len(state) > 17 else None,
        "source": "opensky",
    }


def _fetch_opensky_snapshot() -> tuple[int | None, list[list[Any]]]:
    auth = None
    if OPENSKY_USERNAME and OPENSKY_PASSWORD:
        auth = (OPENSKY_USERNAME, OPENSKY_PASSWORD)

    response = requests.get(OPENSKY_URL, auth=auth, timeout=REQUEST_TIMEOUT_SEC)
    response.raise_for_status()

    payload = response.json()
    observed_at = payload.get("time")
    states = payload.get("states") or []
    return observed_at, states


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "healthy"}, 200


@app.route("/", methods=["GET", "POST"])
def publish_snapshot():
    started_at = time.time()

    if request.method not in {"GET", "POST"}:
        return jsonify({"status": "error", "message": "Unsupported method"}), 405

    try:
        observed_at, states = _fetch_opensky_snapshot()
        topic_path = _topic_path()

        publish_futures = []
        skipped_states = 0

        for state in states:
            event = _normalize_state_vector(observed_at, state)
            if event is None:
                skipped_states += 1
                continue

            publish_futures.append(
                publisher.publish(
                    topic_path,
                    json.dumps(event).encode("utf-8"),
                    schema_version=SCHEMA_VERSION,
                    source="opensky",
                )
            )

        for future in publish_futures:
            future.result()

        duration_ms = int((time.time() - started_at) * 1000)
        return (
            jsonify(
                {
                    "status": "success",
                    "source": "opensky",
                    "topic": PUBSUB_TOPIC,
                    "observed_at": observed_at,
                    "states_received": len(states),
                    "states_published": len(publish_futures),
                    "states_skipped": skipped_states,
                    "duration_ms": duration_ms,
                    "schema_version": SCHEMA_VERSION,
                }
            ),
            200,
        )
    except Exception as exc:
        duration_ms = int((time.time() - started_at) * 1000)
        return (
            jsonify(
                {
                    "status": "error",
                    "message": str(exc),
                    "topic": PUBSUB_TOPIC,
                    "duration_ms": duration_ms,
                }
            ),
            500,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
