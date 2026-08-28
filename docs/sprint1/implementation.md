# Sprint 1 - Implementacion validada

## 1. Resumen

Sprint 1 entrega un walking skeleton operativo de FlightTracker sobre GCP. El cierre validado del sprint incluye:

- pipeline batch BTS con input productivo limpio
- Silver en Parquet
- Gold corregido en BigQuery
- serving batch en Firestore `flights_v1`
- serving live en Firestore `live_flights`
- API REST en Cloud Run
- orquestacion diaria con Cloud Scheduler, Cloud Function y Dataproc
- scripts reproducibles de soporte

## 2. Arquitectura implementada

### Batch

`BTS -> Cloud Storage RAW -> Spark en Dataproc -> Silver -> Gold -> BigQuery`

### Serving batch

`Pub/Sub bts-flights-rows -> validate_and_persist_bts -> Firestore flights_v1 -> API /flights`

### Serving live

`OpenSky -> opensky-producer -> Pub/Sub opensky-states-v1 -> project_opensky_state -> Firestore live_flights -> API /live/*`

## 3. Componentes cerrados en Sprint 1

### 3.1 Ingesta y persistencia batch

- `backend/functions/validate_and_store_bts`
- `backend/functions/split_and_publish_bts`
- `backend/functions/validate_and_persist_bts`
- `pipelines/batch/spark_jobs/bts_etl.py`

### 3.2 Capa analitica

- `pipelines/batch/spark_jobs/etl_gold_modelo_estrella.py`
- dataset `flighttracker_gold`
- tablas `fact_flights`, `dim_airline`, `dim_airport`, `dim_date`
- agregados `agg_on_time_performance` y `agg_delay_distribution`

### 3.3 Serving y API

- `backend/api/get_flights`
- coleccion `flights_v1`
- coleccion `live_flights`
- endpoints `/health`, `/flights`, `/live/flights`, `/live/flights/{icao24}`, `/live/count`

### 3.4 Operacion

- `backend/functions/start_batch_pipeline`
- `infrastructure/scripts/bootstrap.sh`
- `infrastructure/scripts/deploy.sh`
- `infrastructure/scripts/validate.sh`
- `infrastructure/scripts/destroy.sh`

## 4. Evidencia funcional

### Batch y Gold

- `docs/sprint1/evidencias/01-bigquery-kpi.md`
- `docs/sprint1/evidencias/09-batch-bts-extremo-a-extremo.md`
- `docs/sprint1/evidencias/10-consistencia-id-vuelo.md`
- `docs/sprint1/evidencias/11-input-productivo-sin-archivos-prueba.md`

### Serving y API

- `docs/sprint1/evidencias/02-firestore-serving-normalization.md`
- `docs/sprint1/evidencias/03-validacion-skeleton-opensky.md`
- `docs/sprint1/evidencias/12-diagnostico-conectividad-opensky.md`

### Reproducibilidad

- `docs/sprint1/evidencias/04-bootstrap-success.md`
- `docs/sprint1/evidencias/05-deploy-plan-only-validation.md`
- `docs/sprint1/evidencias/06-terraform-plan-clean.md`
- `docs/sprint1/evidencias/07-validation-workflow-pass.md`
- `docs/sprint1/evidencias/08-destroy-workflow-guardrails.md`

## 5. Documentos de apoyo

- `docs/sprint1/arquitectura/arquitectura-referencia-final.md`
- `docs/sprint1/arquitectura/mapeo-preguntas-negocio.md`
- `docs/sprint1/arquitectura/mapeo-tecnologico-gcp.md`
- `docs/sprint1/arquitectura/flujo-implementado-sprint1.md`
- `docs/sprint1/modelos/conceptual.md`
- `docs/sprint1/modelos/logical.md`
- `docs/sprint1/modelos/physical.md`
- `docs/sprint1/modelos/gold-star-schema.md`
- `docs/sprint1/modelos/serving-schema.md`
- `docs/decisiones/ADR-001-almacen-canonico-vuelos-y-contrato-de-proyeccion.md`
- `docs/decisiones/ADR-002-alcance-validado-sprint1.md`

## 6. Reproduccion documentada

### Bootstrap

```bash
bash infrastructure/scripts/bootstrap.sh \
  --project-id flighttracker-505314 \
  --skip-docker-check
```

### Plan controlado

```bash
bash infrastructure/scripts/deploy.sh \
  --project-id flighttracker-505314 \
  --skip-api-build
```

### Validacion

```bash
bash infrastructure/scripts/validate.sh \
  --project-id flighttracker-505314
```

## 7. Cierre del sprint

Sprint 1 queda documentado en el repo como una implementacion validada y demostrable, soportada por evidencias operativas, modelos y scripts reproducibles.
