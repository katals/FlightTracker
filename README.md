# FlightTracker - Sprint 1

FlightTracker integra vuelos historicos BTS, maestros OpenFlights y una rama live demostrada del mismo dominio para exponer productos analiticos y operacionales en Google Cloud.

## Estado actual

- input BTS productivo limpio en `gs://flighttracker-raw-bts/bts/bts_flights_corregido.csv`
- Silver limpio en Parquet
- Gold corregido en BigQuery con hechos, dimensiones y KPI
- serving batch en Firestore `flights_v1`
- serving live en Firestore `live_flights`
- API operativa en Cloud Run con `/health`, `/flights` y `/live/*`
- orquestacion diaria de batch con Cloud Scheduler, Cloud Function y Dataproc
- scripts reproducibles para bootstrap, plan controlado, validacion y destroy seguro

## Aplicacion de usuario final en Sprint 1

El producto consultable del sprint es:

- la API REST en Cloud Run
- las tablas y agregados de BigQuery Gold

URL validada de la API:

- `https://get-flights-api-310107974919.us-central1.run.app`

Consultas rapidas:

```bash
curl -sS "https://get-flights-api-310107974919.us-central1.run.app/health"
curl -sS "https://get-flights-api-310107974919.us-central1.run.app/flights?limit=3"
curl -sS "https://get-flights-api-310107974919.us-central1.run.app/live/flights?limit=3"
```

## Estructura del repo

```text
Sicard/
├── README.md
├── CHANGELOG.md
├── .gitignore
├── .env.example
├── docs/
├── infrastructure/
├── backend/
├── pipelines/
├── database/
├── frontend/
├── tests/
├── docker/
└── .github/
```

## Requisitos

Entorno recomendado:

- Google Cloud Shell

Herramientas requeridas:

- `gcloud`
- `terraform`
- `bash`
- `python3`
- `zip`

Notas:

- `deploy.sh` usa Cloud Build para la imagen de la API, por lo que Docker local no es obligatorio para la ruta validada
- `bootstrap.sh` acepta `--skip-docker-check`

## Configuracion del proyecto GCP

Variables base del proyecto:

- `PROJECT_ID=flighttracker-505314`
- `DATA_REGION=us-central1`
- `BATCH_REGION=us-east1`
- `API_REGION=us-central1`

Referencia de variables:

- `.env.example`

## Recursos principales en GCP

Recursos usados o validados en Sprint 1:

- Cloud Storage: `flighttracker-raw-bts`, `flighttracker-curated-bts`, `flighttracker-scripts`
- Pub/Sub: `bts-flights-rows`, `bts-flights-dlq`, `opensky-states-v1`, `opensky-states-dlq`
- Cloud Functions: `validate_and_store_bts`, `split_and_publish_bts`, `validate_and_persist_bts`, `start_batch_pipeline`, `project_opensky_state`
- Cloud Run: `get-flights-api`, `opensky-producer`
- BigQuery: dataset `flighttracker_gold`
- Firestore: colecciones `flights_v1` y `live_flights`
- Cloud Scheduler: `daily-bts-pipeline`
- Cloud SQL: `flighttracker-db`
- Secret Manager: `cloudsql-postgres-password`

## Reproduccion documentada

### 1. Bootstrap

```bash
bash infrastructure/scripts/bootstrap.sh \
  --project-id flighttracker-505314 \
  --skip-docker-check
```

### 2. Plan controlado

```bash
bash infrastructure/scripts/deploy.sh \
  --project-id flighttracker-505314 \
  --skip-api-build
```

Este flujo:

- empaqueta artefactos
- ejecuta `terraform init`
- ejecuta `terraform validate`
- ejecuta `terraform plan`

Solo aplica cambios si se invoca con `--apply`.

### 3. Validacion operativa

En un clon nuevo, si `validate.sh` se corre sin haber ejecutado antes `deploy.sh`, `terraform validate` falla con `Missing required provider` porque no existe `.terraform/` local con los proveedores descargados. Antes de correr `validate.sh` en un entorno limpio (por ejemplo una sesion nueva de Cloud Shell), ejecuta primero:

```bash
cd infrastructure/terraform
terraform init -backend=false
cd ../..
```

`-backend=false` descarga los proveedores fijados en `.terraform.lock.hcl` sin conectarse al estado remoto, suficiente para validar sintaxis sin tocar el estado real.

```bash
bash infrastructure/scripts/validate.sh \
  --project-id flighttracker-505314
```

Resultado esperado:

```text
PASS  terraform validate
PASS  api health
PASS  api flights
PASS  api live flights
PASS  pubsub topic exists
PASS  firestore collection probe
PASS  bigquery gold fact rows
PASS  latest dataproc job visible
PASS  scheduler job exists
PASS  dq report presence
```

### 4. Profiling y calidad de datos

```bash
gcloud storage cp \
  gs://flighttracker-raw-bts/bts/bts_flights_corregido.csv \
  /tmp/bts_flights_corregido.csv

curl -sS \
  "https://get-flights-api-310107974919.us-central1.run.app/live/flights?limit=50" \
  > /tmp/opensky_live_sample.json

python3 docs/sprint1/data-assessment/generate_profiles.py \
  --bts-csv /tmp/bts_flights_corregido.csv \
  --opensky-json /tmp/opensky_live_sample.json
```

## Scripts operativos

- `infrastructure/scripts/bootstrap.sh`: prepara prerrequisitos base
- `infrastructure/scripts/deploy.sh`: empaqueta artefactos y corre Terraform en modo controlado
- `infrastructure/scripts/validate.sh`: valida el estado observable del sprint
- `infrastructure/scripts/destroy.sh`: documenta destroy seguro con guardrails

## Pruebas y verificacion

Prueba integrada principal:

- `bash infrastructure/scripts/validate.sh --project-id flighttracker-505314`

Verificaciones rapidas adicionales:

- API `/health`
- API `/flights`
- API `/live/flights`
- conteo de `fact_flights` en BigQuery
- profiling reproducible en `docs/sprint1/data-assessment/results/`

## Manejo de secretos y credenciales

- no se incluyen credenciales reales en el repositorio
- las variables sensibles se ejemplifican en `.env.example`
- la clave de Cloud SQL debe manejarse mediante Secret Manager
- `.gitignore` excluye `.env`, secretos locales, estados de Terraform y archivos sensibles

## Estado de automatizacion y excepciones del entorno actual

Estado observado en Sprint 1:

- `bootstrap.sh`, `deploy.sh`, `validate.sh` y `destroy.sh` existen y fueron validados
- `deploy.sh` deja evidencia reproducible de empaquetado y `terraform plan`
- `validate.sh` verifica el estado funcional del sprint

Excepciones que deben entenderse al revisar el proyecto:

- el entorno validado no se presenta como recreado completamente desde cero con un unico `terraform apply`
- `deploy.sh` bloquea `apply` si detecta drift conocido de Terraform
- parte del entorno live actual fue validado sobre recursos ya existentes del proyecto

Referencias:

- `docs/sprint1/evidencias/05-deploy-plan-only-validation.md`
- `docs/sprint1/evidencias/06-terraform-plan-clean.md`
- `docs/sprint1/evidencias/07-validation-workflow-pass.md`

## Estado de CI/CD, logging, monitoreo y alertas

Estado de Sprint 1:

- CI/CD dedicado: no implementado
- monitoreo y alertas dedicadas: no implementados
- logging operativo: disponible a traves de los logs nativos de GCP

Para la presentacion y la entrega, este estado debe comunicarse como:

- implementado cuando exista evidencia
- planificado cuando no exista implementacion todavia

## Documentos clave

### Arquitectura

- `docs/sprint1/implementation.md`
- `docs/sprint1/demo.md`
- `docs/sprint1/arquitectura/arquitectura-referencia-final.md`
- `docs/sprint1/arquitectura/mapeo-preguntas-negocio.md`
- `docs/sprint1/arquitectura/mapeo-tecnologico-gcp.md`
- `docs/sprint1/arquitectura/flujo-implementado-sprint1.md`

### Modelos

- `docs/sprint1/modelos/conceptual.md`
- `docs/sprint1/modelos/logical.md`
- `docs/sprint1/modelos/physical.md`
- `docs/sprint1/modelos/gold-star-schema.md`
- `docs/sprint1/modelos/serving-schema.md`
- `docs/sprint1/modelos/cloudsql-schema.sql`

### Evidencias

- `docs/sprint1/evidencias/01-bigquery-kpi.md`
- `docs/sprint1/evidencias/02-firestore-serving-normalization.md`
- `docs/sprint1/evidencias/03-validacion-skeleton-opensky.md`
- `docs/sprint1/evidencias/04-bootstrap-success.md`
- `docs/sprint1/evidencias/05-deploy-plan-only-validation.md`
- `docs/sprint1/evidencias/06-terraform-plan-clean.md`
- `docs/sprint1/evidencias/07-validation-workflow-pass.md`
- `docs/sprint1/evidencias/08-destroy-workflow-guardrails.md`
- `docs/sprint1/evidencias/09-batch-bts-extremo-a-extremo.md`
- `docs/sprint1/evidencias/10-consistencia-id-vuelo.md`
- `docs/sprint1/evidencias/11-input-productivo-sin-archivos-prueba.md`
- `docs/sprint1/evidencias/12-diagnostico-conectividad-opensky.md`

### Decisiones tecnicas

- `docs/decisiones/ADR-001-almacen-canonico-vuelos-y-contrato-de-proyeccion.md`
- `docs/decisiones/ADR-002-alcance-validado-sprint1.md`

## Codigo relevante

- ETL batch BTS: `pipelines/batch/spark_jobs/bts_etl.py`
- ETL Gold: `pipelines/batch/spark_jobs/etl_gold_modelo_estrella.py`
- API: `backend/api/get_flights/`
- funciones batch: `backend/functions/`
- productor live: `pipelines/streaming/productor_opensky/`

## Equipo

- Agustin Figueroa 
- Gabriela  Martinez 
- Juan Simon Ospina
- Juan Carlos Muñoz
