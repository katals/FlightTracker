# Evidencia 03 - Validacion del skeleton OpenSky

**Fecha:** 2026-08-25  
**Punto del plan:** Workstream C / `C8`

## Objetivo

Validar la rama live demostrada en Sprint 1:

`OpenSky -> Pub/Sub -> Firestore live_flights -> API live`

## Evidencia validada

### 1. Topicos dedicados

Se utilizaron:

- `opensky-states-v1`
- `opensky-states-dlq`

### 2. Productor desplegado

Servicio:

- `opensky-producer` en Cloud Run `us-central1`

Validacion:

- `GET /health` respondio `{"status":"healthy"}`

### 3. Publicacion y proyeccion

Se publico un evento en `opensky-states-v1` con `icao24=abc123`.

Resultado observado:

- `project_opensky_state` proyecto el documento en `live_flights`
- la API respondio correctamente:
  - `GET /live/flights?limit=5`
  - `GET /live/flights/abc123`
  - `GET /live/count`

## Conclusion

La rama live demostrada en Sprint 1 cuenta con:

- productor desplegado
- topico dedicado
- proyeccion operativa
- consulta live por API

## Estado

**Completado** para Sprint 1.
