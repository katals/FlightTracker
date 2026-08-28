# Gold Star Schema

## Estado real en Sprint 1

La capa Gold existe en BigQuery bajo el dataset:

- `flighttracker_gold`

## Tablas fisicas reales

### `fact_flights`

Grano:

- un vuelo historico del BTS ya normalizado y enriquecido con claves de dimensiones

Campos principales:

- `flight_id`
- `date_key`
- `airline_key`
- `origin_key`
- `dest_key`
- `dep_delay`
- `arr_delay`
- `cancelled`
- `air_time`
- `distance`
- `dep_time`
- `arr_time`

### `dim_airline`

Campos principales:

- `airline_key`
- `iata_code`
- `icao_code`
- `name`
- `country`

Origen:

- OpenFlights deduplicado por `iata_code`

### `dim_airport`

Campos principales:

- `airport_key`
- `iata_code`
- `icao_code`
- `name`
- `city`
- `country`
- `latitude`
- `longitude`
- `altitude`

Origen:

- OpenFlights deduplicado por `iata_code`

### `dim_date`

Campos principales:

- `date_key`
- `full_date`
- `year`
- `month`
- `day`
- `day_of_week`
- `is_weekend`
- `quarter`
- `day_name`

Origen:

- secuencia real entre `min(FL_DATE)` y `max(FL_DATE)`

## Agregados KPI reales

### `agg_on_time_performance`

Indicador principal:

- puntualidad usando `arr_delay <= 15`

Campos:

- `airline_key`
- `origin_key`
- `dest_key`
- `total_flights`
- `on_time_flights`
- `avg_arr_delay`
- `on_time_percentage`

### `agg_delay_distribution`

Uso:

- distribucion de retrasos para analisis agregado

## Alineacion importante

El `flight_id` de Gold debe mantenerse alineado con el contrato canonico usado por la rama operacional. Ese ajuste ya fue aplicado durante la reconstruccion validada de Sprint 1.
