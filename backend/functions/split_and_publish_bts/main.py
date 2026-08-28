import functions_framework
from google.cloud import storage, pubsub_v1
import csv
import hashlib
import os
import json
from datetime import datetime, timezone


def _normalise_date(value):
    """Return the BTS date in ISO-8601 format without accepting silent changes."""
    value = (value or "").strip()
    for date_format in ("%Y-%m-%d", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            pass
    return value


def _canonical_event(row, bucket_name, file_name, generation, row_number):
    """Build the versioned event consumed by every operational data store."""
    carrier = (row.get("OP_CARRIER") or row.get("OP_UNIQUE_CARRIER") or "").strip().upper()
    flight_date = _normalise_date(row.get("FL_DATE"))
    origin = (row.get("ORIGIN") or "").strip().upper()
    destination = (row.get("DEST") or "").strip().upper()
    flight_number = str(row.get("OP_CARRIER_FL_NUM") or "").strip()
    departure_time = str(row.get("DEP_TIME") or "").strip()

    source_uri = f"gs://{bucket_name}/{file_name}"
    source_identity = f"{source_uri}|{generation}|{row_number}"
    business_identity = "|".join(
        [flight_date, carrier, flight_number, origin, destination, departure_time]
    )

    event = dict(row)
    event.update(
        {
            "schema_version": "flight.curated.v1",
            "event_id": hashlib.sha256(source_identity.encode("utf-8")).hexdigest(),
            "flight_id": hashlib.sha256(business_identity.encode("utf-8")).hexdigest(),
            "source_uri": source_uri,
            "source_generation": str(generation or "unknown"),
            "source_row_number": row_number,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "flight_date": flight_date,
            "carrier": carrier,
            "flight_number": flight_number,
            "origin": origin,
            "destination": destination,
            # Compatibility aliases for consumers still using the BTS field names.
            "OP_CARRIER": carrier,
            "FL_DATE": flight_date,
        }
    )
    return event


@functions_framework.cloud_event
def split_and_publish_bts(cloud_event):
    data = cloud_event.data
    bucket_name = data['bucket']
    file_name = data['name']

    if not file_name.endswith('.csv'):
        print(f"Ignoring non-CSV object: {file_name}")
        return

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    project_id = os.environ["GCP_PROJECT_ID"]
    topic_name = os.environ.get("PUBSUB_TOPIC", "bts-flights-rows")
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)
    generation = data.get("generation")
    pending = []
    published_rows = 0
    batch_size = 1_000

    try:
        # Blob.open streams GCS data and avoids loading the full CSV into memory or /tmp.
        with blob.open("rt", encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            for row_number, row in enumerate(reader, start=2):
                event = _canonical_event(row, bucket_name, file_name, generation, row_number)
                pending.append(
                    publisher.publish(topic_path, json.dumps(event).encode("utf-8"))
                )
                published_rows += 1

                if len(pending) >= batch_size:
                    for future in pending:
                        future.result()
                    pending.clear()
                    print(f"Published {published_rows} rows from {file_name}")

        for future in pending:
            future.result()
        print(f"Published {published_rows} rows from {file_name}")
    except Exception:
        # Eventarc must observe the failure so the source object can be retried.
        print(f"Error processing {file_name}")
        raise
