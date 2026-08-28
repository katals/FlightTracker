# Modelo Conceptual

## Objetivo

Describir las entidades de negocio minimas de FlightTracker en Sprint 1 sin atarlas todavia a una tecnologia especifica.

## Entidades principales

### Flight

Representa un vuelo historico del BTS observado como evento operacional.

Atributos clave:

- `flight_date`
- `carrier`
- `flight_number`
- `origin`
- `destination`
- `dep_time`
- `arr_time`
- `dep_delay`
- `arr_delay`
- `cancelled`
- `air_time`
- `distance`

### Airline

Representa la aerolinea operadora del vuelo.

Atributos clave:

- `iata_code`
- `icao_code`
- `name`
- `country`

### Airport

Representa un aeropuerto origen o destino.

Atributos clave:

- `iata_code`
- `icao_code`
- `name`
- `city`
- `country`
- `latitude`
- `longitude`
- `altitude`

### Route

Representa el trayecto entre un aeropuerto origen y un aeropuerto destino.

Atributos clave:

- `origin_airport`
- `destination_airport`

### FlightObservation

Representa una observacion de un vuelo en una linea temporal operacional o live.

En Sprint 1 tiene dos variantes:

- observacion batch del BTS
- observacion live de OpenSky

Atributos clave:

- `observed_at`
- `source`
- `event_id`
- `flight_id` o `icao24`

### IngestionRun

Representa una ejecucion de ingesta o procesamiento.

Atributos clave:

- `source_uri`
- `source_generation`
- `processed_at`
- `schema_version`
- `status`

## Relaciones

- Un `Flight` es operado por una `Airline`.
- Un `Flight` sale de un `Airport` origen y llega a un `Airport` destino.
- Un `Route` conecta dos `Airport`.
- Un `FlightObservation` describe el estado de un `Flight` o de una aeronave live.
- Un `IngestionRun` produce muchas `FlightObservation`.

## Lectura de Sprint 1

- Batch historico: `BTS -> Flight`
- Master data: `OpenFlights -> Airline, Airport`
- Live temporal: `OpenSky -> FlightObservation`
