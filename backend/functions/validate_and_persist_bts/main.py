import functions_framework
from google.cloud import firestore
import json
from datetime import datetime, timezone
import base64
import hashlib
import os


def _normalise_date(value):
    value = str(value or "").strip()
    for date_format in ("%Y-%m-%d", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            pass
    return value


def _empty_to_none(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return text


def parse_optional_float(value):
    text = _empty_to_none(value)
    if text is None:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def parse_optional_int(value):
    text = _empty_to_none(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def parse_bool(value):
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "1.0", "true", "t", "yes", "y"}:
        return True
    if text in {"0", "0.0", "false", "f", "no", "n", ""}:
        return False
    return False


def _normalise_record(row):
    carrier = str(row.get("carrier") or row.get("OP_CARRIER") or row.get("OP_UNIQUE_CARRIER") or "").strip().upper()
    flight_date = _normalise_date(row.get("flight_date") or row.get("FL_DATE"))
    origin = str(row.get("origin") or row.get("ORIGIN") or "").strip().upper()
    destination = str(row.get("destination") or row.get("DEST") or "").strip().upper()
    flight_number = str(row.get("flight_number") or row.get("OP_CARRIER_FL_NUM") or "").strip()
    departure_time = parse_optional_int(row.get("DEP_TIME"))

    if not all((flight_date, carrier, flight_number, origin, destination)):
        raise ValueError("Invalid flight event: required business fields are missing")

    business_identity = "|".join(
        [
            flight_date,
            carrier,
            flight_number,
            origin,
            destination,
            "" if departure_time is None else str(departure_time),
        ]
    )
    normalised = dict(row)
    normalised.update(
        {
            "schema_version": row.get("schema_version", "flight.curated.v1"),
            "flight_id": row.get("flight_id") or hashlib.sha256(business_identity.encode("utf-8")).hexdigest(),
            "flight_date": flight_date,
            "carrier": carrier,
            "flight_number": flight_number,
            "origin": origin,
            "destination": destination,
            "dep_time": departure_time,
            "dep_delay": parse_optional_float(row.get("DEP_DELAY")),
            "arr_time": parse_optional_int(row.get("ARR_TIME")),
            "arr_delay": parse_optional_float(row.get("ARR_DELAY")),
            "cancelled": parse_bool(row.get("CANCELLED")),
            "air_time": parse_optional_float(row.get("AIR_TIME")),
            "distance": parse_optional_float(row.get("DISTANCE")),
            "event_id": row.get("event_id"),
            "source_uri": row.get("source_uri"),
            "source_generation": row.get("source_generation"),
            "source_row_number": parse_optional_int(row.get("source_row_number")),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            # Compatibility aliases while Firestore remains the temporal projection.
            "FL_DATE": flight_date,
            "OP_CARRIER": carrier,
            "OP_CARRIER_FL_NUM": flight_number,
            "ORIGIN": origin,
            "DEST": destination,
            "DEP_TIME": departure_time,
            "DEP_DELAY": parse_optional_float(row.get("DEP_DELAY")),
            "ARR_TIME": parse_optional_int(row.get("ARR_TIME")),
            "ARR_DELAY": parse_optional_float(row.get("ARR_DELAY")),
            "CANCELLED": parse_bool(row.get("CANCELLED")),
            "AIR_TIME": parse_optional_float(row.get("AIR_TIME")),
            "DISTANCE": parse_optional_float(row.get("DISTANCE")),
        }
    )
    return normalised


@functions_framework.cloud_event
def validate_and_persist_bts(cloud_event):
    message_data = base64.b64decode(cloud_event.data['message']['data']).decode('utf-8')
    row = json.loads(message_data)

    try:
        row = _normalise_record(row)
    except ValueError as e:
        print(f"Invalid record: {e}")
        return

    db = firestore.Client()
    collection_name = os.environ.get("FIRESTORE_COLLECTION", "flights")
    # Pub/Sub and Eventarc are at-least-once; a deterministic document ID is required.
    doc_ref = db.collection(collection_name).document(row['flight_id'])
    doc_ref.set(row)
    print(
        f"Flight persisted in {collection_name}: "
        f"{row['carrier']}{row['flight_number']} ({row['flight_id']})"
    )
