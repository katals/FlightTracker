#!/usr/bin/env python3
"""Generate reproducible profiling artifacts for Sprint 1."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen


AIRLINES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
IATA_AIRLINE_RE = re.compile(r"^[A-Z0-9]{2}$")
IATA_AIRPORT_RE = re.compile(r"^[A-Z]{3}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Sprint 1 profiling results.")
    parser.add_argument("--bts-csv", required=True, help="Local path to BTS productive CSV.")
    parser.add_argument(
        "--opensky-json",
        required=True,
        help="Local path to OpenSky sample JSON exported from the live API.",
    )
    parser.add_argument(
        "--results-dir",
        default=str(Path(__file__).resolve().parent / "results"),
        help="Output directory for JSON/CSV artifacts.",
    )
    return parser.parse_args()


def safe_float(value: Any) -> float | None:
    if value in (None, "", "NULL", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    number = safe_float(value)
    if number is None:
        return None
    return int(number)


def parse_bts_date(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%Y %I:%M:%S %p"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    lower_value = ordered[lower]
    upper_value = ordered[upper]
    return lower_value + (upper_value - lower_value) * (position - lower)


def series_stats(values: list[float]) -> dict[str, float | None]:
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "max": max(values) if values else None,
        "mean": round(statistics.fmean(values), 4) if values else None,
    }


def null_summary(rows: list[dict[str, Any]], columns: list[str]) -> dict[str, dict[str, float]]:
    row_count = len(rows) or 1
    summary: dict[str, dict[str, float]] = {}
    for column in columns:
        null_count = sum(1 for row in rows if row.get(column) in (None, "", "NULL", "None"))
        summary[column] = {
            "null_count": null_count,
            "null_pct": round((null_count / row_count) * 100, 4),
        }
    return summary


def load_csv_from_url(url: str, columns: list[str]) -> list[dict[str, Any]]:
    with urlopen(url) as response:
        decoded = (line.decode("utf-8", errors="replace") for line in response)
        reader = csv.reader(decoded)
        rows = []
        for record in reader:
            if len(record) < len(columns):
                record += [""] * (len(columns) - len(record))
            rows.append(dict(zip(columns, record)))
        return rows


def profile_bts(csv_path: Path) -> tuple[dict[str, Any], dict[str, float]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    columns = reader.fieldnames or []
    row_count = len(rows)
    duplicate_rows = row_count - len({tuple((column, row.get(column, "")) for column in columns) for row in rows})
    parsed_dates = [parse_bts_date(row.get("FL_DATE")) for row in rows]
    valid_dates = [date.strftime("%Y-%m-%d") for date in parsed_dates if date]

    carriers = Counter((row.get("OP_CARRIER") or row.get("OP_UNIQUE_CARRIER") or "").strip() for row in rows)
    origins = Counter((row.get("ORIGIN") or "").strip() for row in rows)
    destinations = Counter((row.get("DEST") or "").strip() for row in rows)
    cancelled = Counter(str(safe_int(row.get("CANCELLED")) or 0) for row in rows)
    dep_delay_values = [value for value in (safe_float(row.get("DEP_DELAY")) for row in rows) if value is not None]
    arr_delay_values = [value for value in (safe_float(row.get("ARR_DELAY")) for row in rows) if value is not None]

    invalid_origin = sum(1 for code in origins if code and not IATA_AIRPORT_RE.match(code))
    invalid_dest = sum(1 for code in destinations if code and not IATA_AIRPORT_RE.match(code))
    invalid_carrier = sum(1 for code in carriers if code and not IATA_AIRLINE_RE.match(code))
    invalid_dates = sum(1 for date in parsed_dates if date is None)

    profile = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(csv_path),
        "row_count": row_count,
        "column_count": len(columns),
        "duplicate_rows": duplicate_rows,
        "duplicate_row_pct": round((duplicate_rows / row_count) * 100, 4) if row_count else 0.0,
        "null_summary": null_summary(rows, columns),
        "date_min": min(valid_dates) if valid_dates else None,
        "date_max": max(valid_dates) if valid_dates else None,
        "carriers": {"distinct": len(carriers), "top_10": carriers.most_common(10)},
        "origins": {"distinct": len(origins), "top_10": origins.most_common(10)},
        "destinations": {"distinct": len(destinations), "top_10": destinations.most_common(10)},
        "invalid_iata": {
            "carrier_codes": invalid_carrier,
            "origin_codes": invalid_origin,
            "destination_codes": invalid_dest,
        },
        "invalid_date_rows": invalid_dates,
        "cancelled_distribution": dict(cancelled),
        "dep_delay_distribution": series_stats(dep_delay_values),
        "arr_delay_distribution": series_stats(arr_delay_values),
    }

    total_cells = row_count * len(columns) if columns else 1
    null_cells = sum(item["null_count"] for item in profile["null_summary"].values())
    completeness = max(0.0, 1 - (null_cells / total_cells))
    validity_penalty = (invalid_carrier + invalid_origin + invalid_dest + invalid_dates) / max(row_count, 1)
    validity = max(0.0, 1 - validity_penalty)
    uniqueness = max(0.0, 1 - (duplicate_rows / max(row_count, 1)))
    consistency = max(0.0, 1 - ((invalid_origin + invalid_dest) / max(row_count, 1)))
    accuracy_proxy = 1.0

    return profile, {
        "completeness": completeness,
        "validity": validity,
        "uniqueness": uniqueness,
        "consistency": consistency,
        "accuracy_proxy": accuracy_proxy,
    }


def profile_openflights_airlines() -> tuple[dict[str, Any], dict[str, float]]:
    columns = ["id", "name", "alias", "iata", "icao", "callsign", "country", "active"]
    rows = load_csv_from_url(AIRLINES_URL, columns)
    row_count = len(rows)
    iata_codes = [row["iata"].strip() for row in rows]
    valid_codes = [code for code in iata_codes if code and code != "\\N"]
    duplicates = len(valid_codes) - len(set(valid_codes))
    null_iata = sum(1 for code in iata_codes if not code or code == "\\N")
    invalid_iata = sum(1 for code in valid_codes if not IATA_AIRLINE_RE.match(code))

    profile = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": AIRLINES_URL,
        "row_count": row_count,
        "duplicate_iata": duplicates,
        "null_iata": null_iata,
        "invalid_iata_format": invalid_iata,
    }

    completeness = max(0.0, 1 - (null_iata / max(row_count, 1)))
    validity = max(0.0, 1 - (invalid_iata / max(row_count, 1)))
    uniqueness = max(0.0, 1 - (duplicates / max(len(valid_codes), 1)))
    consistency = validity
    accuracy_proxy = 1.0

    return profile, {
        "completeness": completeness,
        "validity": validity,
        "uniqueness": uniqueness,
        "consistency": consistency,
        "accuracy_proxy": accuracy_proxy,
    }


def profile_openflights_airports() -> tuple[dict[str, Any], dict[str, float]]:
    columns = [
        "id",
        "name",
        "city",
        "country",
        "iata",
        "icao",
        "lat",
        "lon",
        "alt",
        "timezone",
        "dst",
        "tz_db",
        "type",
        "source",
    ]
    rows = load_csv_from_url(AIRPORTS_URL, columns)
    row_count = len(rows)
    iata_codes = [row["iata"].strip() for row in rows]
    valid_codes = [code for code in iata_codes if code and code != "\\N"]
    duplicates = len(valid_codes) - len(set(valid_codes))
    null_lat_lon = sum(
        1
        for row in rows
        if row["lat"].strip() in ("", "\\N") or row["lon"].strip() in ("", "\\N")
    )
    invalid_iata = sum(1 for code in valid_codes if not IATA_AIRPORT_RE.match(code))
    invalid_coordinates = 0
    for row in rows:
        lat = safe_float(row["lat"])
        lon = safe_float(row["lon"])
        if lat is None or lon is None:
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            invalid_coordinates += 1

    profile = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": AIRPORTS_URL,
        "row_count": row_count,
        "duplicate_iata": duplicates,
        "null_lat_lon": null_lat_lon,
        "invalid_iata_format": invalid_iata,
        "invalid_coordinate_ranges": invalid_coordinates,
    }

    completeness = max(0.0, 1 - (null_lat_lon / max(row_count, 1)))
    validity = max(0.0, 1 - ((invalid_iata + invalid_coordinates) / max(row_count, 1)))
    uniqueness = max(0.0, 1 - (duplicates / max(len(valid_codes), 1)))
    consistency = validity
    accuracy_proxy = 1.0

    return profile, {
        "completeness": completeness,
        "validity": validity,
        "uniqueness": uniqueness,
        "consistency": consistency,
        "accuracy_proxy": accuracy_proxy,
    }


def load_opensky_rows(opensky_path: Path) -> list[dict[str, Any]]:
    with opensky_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload
    return []


def profile_opensky(opensky_path: Path) -> tuple[dict[str, Any], dict[str, float]]:
    rows = load_opensky_rows(opensky_path)
    row_count = len(rows)
    duplicate_icao24 = row_count - len({str(row.get("icao24", "")).lower() for row in rows if row.get("icao24")})
    null_longitude = sum(1 for row in rows if row.get("longitude") is None)
    null_latitude = sum(1 for row in rows if row.get("latitude") is None)
    null_callsign = sum(1 for row in rows if not str(row.get("callsign") or "").strip())
    observed_values = [str(row.get("observed_at")) for row in rows if row.get("observed_at")]
    freshness = None
    if observed_values:
        parsed = []
        for value in observed_values:
            try:
                parsed.append(datetime.fromisoformat(value.replace("Z", "+00:00")))
            except ValueError:
                continue
        if parsed:
            freshest = max(parsed)
            freshness = round((datetime.now(timezone.utc) - freshest).total_seconds(), 2)

    profile = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(opensky_path),
        "states": row_count,
        "null_longitude": null_longitude,
        "null_latitude": null_latitude,
        "null_callsign": null_callsign,
        "duplicate_icao24": duplicate_icao24,
        "timestamp_freshness_seconds": freshness,
    }

    total_cells = row_count * 4 if row_count else 1
    completeness = max(0.0, 1 - ((null_longitude + null_latitude + null_callsign) / total_cells))
    validity = 1.0
    uniqueness = max(0.0, 1 - (duplicate_icao24 / max(row_count, 1)))
    consistency = 1.0
    accuracy_proxy = 1.0 if freshness is None else max(0.0, 1 - min(freshness / 3600, 1))

    return profile, {
        "completeness": completeness,
        "validity": validity,
        "uniqueness": uniqueness,
        "consistency": consistency,
        "accuracy_proxy": accuracy_proxy,
    }


def dq_score(metrics: dict[str, float]) -> float:
    weights = {
        "completeness": 0.30,
        "validity": 0.25,
        "uniqueness": 0.20,
        "consistency": 0.15,
        "accuracy_proxy": 0.10,
    }
    return round(sum(metrics[key] * weight for key, weight in weights.items()), 4)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def write_dq_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "dataset",
        "row_count",
        "completeness",
        "validity",
        "uniqueness",
        "consistency",
        "accuracy_proxy",
        "dq_score",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    results_dir = Path(args.results_dir).resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    bts_profile, bts_metrics = profile_bts(Path(args.bts_csv))
    airlines_profile, airlines_metrics = profile_openflights_airlines()
    airports_profile, airports_metrics = profile_openflights_airports()
    opensky_profile, opensky_metrics = profile_opensky(Path(args.opensky_json))

    write_json(results_dir / "bts_profile.json", bts_profile)
    write_json(results_dir / "openflights_airlines_profile.json", airlines_profile)
    write_json(results_dir / "openflights_airports_profile.json", airports_profile)
    write_json(results_dir / "opensky_profile.json", opensky_profile)

    summary_rows = [
        {
            "dataset": "bts",
            "row_count": bts_profile["row_count"],
            **{key: round(value, 4) for key, value in bts_metrics.items()},
            "dq_score": dq_score(bts_metrics),
        },
        {
            "dataset": "openflights_airlines",
            "row_count": airlines_profile["row_count"],
            **{key: round(value, 4) for key, value in airlines_metrics.items()},
            "dq_score": dq_score(airlines_metrics),
        },
        {
            "dataset": "openflights_airports",
            "row_count": airports_profile["row_count"],
            **{key: round(value, 4) for key, value in airports_metrics.items()},
            "dq_score": dq_score(airports_metrics),
        },
        {
            "dataset": "opensky",
            "row_count": opensky_profile["states"],
            **{key: round(value, 4) for key, value in opensky_metrics.items()},
            "dq_score": dq_score(opensky_metrics),
        },
    ]
    write_dq_summary(results_dir / "dq_summary.csv", summary_rows)

    print(f"Profiling artifacts generated in: {results_dir}")


if __name__ == "__main__":
    main()
