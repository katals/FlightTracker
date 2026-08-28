# Esquema de Serving

## Alcance

Este documento describe las colecciones de serving usadas en Sprint 1.

## Coleccion `flights_v1`

Proposito:

- lectura batch para la API REST

Identificador:

- `flight_id`

Campos canonicos:

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

Patrones de consulta:

- lista acotada de vuelos
- filtro por aerolinea
- filtro por fecha

## Coleccion `live_flights`

Proposito:

- lectura live del ultimo estado conocido

Identificador:

- `icao24`

Campos canonicos:

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

Patrones de consulta:

- lista de ultimos vuelos live
- lectura por `icao24`
- conteo de vuelos live
