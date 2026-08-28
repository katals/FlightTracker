# ADR-001: Almacen canonico de vuelos y contrato de proyeccion

## Estado

Aprobado para Sprint 1.

## Decision

La fuente limpia del batch es Silver en Parquet y la capa analitica consultable es Gold en BigQuery.

La proyeccion operacional usada por la API se construye sobre Firestore mediante un contrato de lectura desacoplado del motor de almacenamiento.

## Contrato de datos

El contrato canonico `flight.curated.v1` incluye, como minimo:

- `event_id`
- `flight_id`
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

## Reglas del identificador

- `event_id` conserva trazabilidad del origen
- `flight_id` usa la identidad de negocio normalizada
- el documento de Firestore usa `flight_id` como identificador
- reintentos o reprocesos del mismo vuelo no generan duplicados logicos

## Puerto de lectura

La API depende de `FlightRepository` y no de un SDK especifico de base de datos.

Metodos usados en Sprint 1:

- `list_flights`
- `list_live_flights`
- `get_live_flight`

## Reglas operativas

1. Silver es la referencia limpia del batch.
2. Gold es la capa analitica consultable.
3. Firestore soporta la proyeccion usada por la API.
4. Los cambios incompatibles del contrato deben versionarse.
5. Los recursos persistentes se gestionan mediante Terraform y scripts de soporte.

## Consecuencias

- el serving batch y live comparten contratos consistentes con la API
- el `flight_id` debe mantenerse alineado entre la rama operacional y la analitica
- la documentacion tecnica del repo describe el estado validado del sprint
