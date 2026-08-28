# Modelo Fisico

## Alcance

Este documento resume las estructuras fisicas usadas en Sprint 1.

## Cloud SQL

Base transaccional maestra para OpenFlights:

- tabla `airlines`
- tabla `airports`

Referencia:

- `cloudsql-schema.sql`

## Firestore

Colecciones operativas:

### `flights_v1`

Campos clave:

- `flight_id`
- `event_id`
- `schema_version`
- `processed_at`
- `flight_date`
- `carrier`
- `flight_number`
- `origin`
- `destination`
- `dep_time`
- `dep_delay`
- `arr_time`
- `arr_delay`
- `cancelled`
- `air_time`
- `distance`
- `source_uri`
- `source_generation`
- `source_row_number`

### `live_flights`

Campos clave:

- `icao24`
- `event_id`
- `schema_version`
- `observed_at`
- `processed_at`
- `callsign`
- `origin_country`
- `longitude`
- `latitude`
- `baro_altitude`
- `velocity`
- `heading`
- `on_ground`

## BigQuery Gold

Dataset:

- `flighttracker_gold`

Tablas:

- `fact_flights`
- `dim_airline`
- `dim_airport`
- `dim_date`
- `agg_on_time_performance`
- `agg_delay_distribution`

Referencia:

- `gold-star-schema.md`
