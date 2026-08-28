# Evidencia 02 - Normalizacion de serving en Firestore

**Fecha:** 2026-08-25  
**Punto del plan:** 38.12 / "Normalizar datos de serving"

## Problema corregido

La coleccion operativa usada por la API mezclaba tipos en los mismos campos:

- `DEP_TIME` podia llegar como `str` o `float`
- `DEP_DELAY` podia llegar como `str` o `float`
- `ARR_DELAY` podia llegar como `str` o `float`
- `CANCELLED` podia llegar como `str` o `float`

Eso hacia que la demo no tuviera un esquema consistente.

## Cambio aplicado

- `validate_and_persist_bts` fue redeployado con `FIRESTORE_COLLECTION=flights_v1`
- la funcion normaliza tipos antes de persistir
- `get-flights-api` fue redeployado con `FIRESTORE_COLLECTION=flights_v1`

## Evidencia de escritura

Log confirmado en Cloud Run / Cloud Functions Gen2:

```text
Flight persisted in flights_v1: AA1234 (272f5d9c5a91351f07b985b5e8eabdbae4de664b5919fc38d484f6013f292e29)
```

## Evidencia de lectura por API

Consulta ejecutada:

```bash
curl -sS "https://get-flights-api-310107974919.us-central1.run.app/flights?limit=5"
```

Respuesta observada:

```json
{
  "status": "success",
  "count": 1,
  "data": [
    {
      "flight_id": "272f5d9c5a91351f07b985b5e8eabdbae4de664b5919fc38d484f6013f292e29",
      "schema_version": "flight.curated.v1",
      "processed_at": "2026-08-25T02:18:20.289362+00:00",
      "flight_date": "2026-01-15",
      "carrier": "AA",
      "flight_number": "1234",
      "origin": "MIA",
      "destination": "JFK",
      "dep_time": 930,
      "dep_delay": 23.0,
      "arr_time": 1245,
      "arr_delay": 17.0,
      "cancelled": false,
      "air_time": 165.0,
      "distance": 1090.0,
      "source_uri": "gs://flighttracker-raw-bts/bts/bts_flights_corregido.csv",
      "source_generation": "manual-test",
      "source_row_number": 1,
      "event_id": "manual-bts-002"
    }
  ]
}
```

## Conclusiones

- la API ya consume la coleccion limpia `flights_v1`
- los campos normalizados salen con tipos consistentes
- se mantuvieron aliases legacy en el documento para no romper compatibilidad, pero la demo debe usar los campos canonicos en minuscula

## Estado

**Completado** para Sprint 1 demo.
