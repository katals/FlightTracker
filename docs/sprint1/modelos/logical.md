# Modelo Logico

## Objetivo

Explicar las claves, relaciones y contratos logicos usados en Sprint 1 entre la rama batch, la proyeccion operacional y la capa Gold.

## Identificadores principales

### `event_id`

Identificador idempotente del evento operacional.

Regla documentada en ADR:

- `sha256(source_uri + source_generation + row_number)`

Uso:

- trazabilidad del evento origen
- control de reintentos

### `flight_id`

Identificador deterministico de negocio para un vuelo batch.

Contrato usado en Sprint 1:

- `flight_date`
- `carrier`
- `flight_number`
- `origin`
- `destination`
- `dep_time`

normalizados y luego hasheados con SHA-256.

Limitacion conocida:

- cuando BTS no expone hora programada, `dep_time` actua como aproximacion
- en vuelos cancelados la estabilidad del identificador depende de la disponibilidad del campo

### `icao24`

Clave natural usada para la coleccion live de OpenSky.

Uso:

- documento en `live_flights`
- lookup directo por aeronave

## Relaciones logicas

### Batch operacional

`BTS row -> event_id -> flight_id -> flights_v1`

Relacion:

- muchas filas BTS entran como eventos
- cada evento se proyecta a un documento operacional
- el documento queda identificado por `flight_id`

### Serving live

`OpenSky state -> event_id -> icao24 -> live_flights`

Relacion:

- cada snapshot produce estados
- cada estado se sobreescribe por `icao24`
- el serving live conserva el ultimo estado conocido

### Gold analitico

`Silver flight -> flight_id -> fact_flights`

Relacion:

- `fact_flights.flight_id` conserva el contrato canonico del pipeline batch
- `dim_airline` y `dim_airport` usan surrogate keys
- `dim_date` usa `date_key`

## Claves naturales vs surrogate keys

### Naturales

- `iata_code` para aerolineas
- `iata_code` para aeropuertos
- `icao24` para live aircraft state

### Deterministicas

- `flight_id`
- `event_id`

### Surrogate

- `airline_key`
- `airport_key`
- `date_key`

## Patrones de consulta aprobados

### API batch

- vuelos por fecha
- vuelos por aerolinea
- lectura acotada por limite

### API live

- ultimos vuelos live
- vuelo live por `icao24`
- conteo live

### Analytics

- puntualidad por aerolinea y ruta
- distribucion de retrasos
- joins por fecha, aerolinea y aeropuerto
