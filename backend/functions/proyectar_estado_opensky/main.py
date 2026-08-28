import base64
import json
from datetime import datetime, timezone

import functions_framework
from google.cloud import firestore


def _normalise_live_state(payload: dict) -> dict:
    icao24 = str(payload.get("icao24") or "").strip().lower()
    if not icao24:
        raise ValueError("Invalid OpenSky event: missing icao24")

    observed_at = payload.get("observed_at")
    processed_at = datetime.now(timezone.utc).isoformat()

    normalised = dict(payload)
    normalised.update(
        {
            "schema_version": payload.get("schema_version", "opensky.state.v1"),
            "icao24": icao24,
            "source": payload.get("source", "opensky"),
            "processed_at": processed_at,
            "last_seen_at": observed_at,
        }
    )
    return normalised


@functions_framework.cloud_event
def project_opensky_state(cloud_event):
    message_data = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    payload = json.loads(message_data)

    try:
        row = _normalise_live_state(payload)
    except ValueError as exc:
        print(f"Invalid OpenSky record: {exc}")
        return

    db = firestore.Client()
    doc_ref = db.collection("live_flights").document(row["icao24"])
    doc_ref.set(row)
    print(f"Live flight projected: {row['icao24']}")
