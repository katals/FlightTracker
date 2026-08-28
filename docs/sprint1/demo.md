# Guion de demostracion - Sprint 1

## 1. Resumen

Este documento describe la secuencia de demostracion de Sprint 1: que se muestra, con que comando, y que evidencia lo respalda. Cada paso cita su archivo en `docs/sprint1/evidencias/`.

## 2. Apertura

Se presenta `docs/sprint1/arquitectura/arquitectura-referencia-final.md` como arquitectura de referencia validada: batch BTS, serving en Firestore, API en Cloud Run, rama live hacia OpenSky.

Se recorre `docs/sprint1/arquitectura/mapeo-preguntas-negocio.md`: seis preguntas de negocio, cada una con su fuente, procesamiento, storage y producto demostrable.

## 3. Bootstrap del entorno

**Evidencia:** `04-bootstrap-success.md`

```bash
bash infrastructure/scripts/bootstrap.sh \
  --project-id flighttracker-505314 \
  --skip-docker-check
```

Valida autenticacion, proyecto activo y backend remoto de Terraform. No crea recursos de negocio fuera de Terraform.

## 4. Plan controlado y Terraform limpio

**Evidencia:** `05-deploy-plan-only-validation.md`, `06-terraform-plan-clean.md`

```bash
cd infrastructure/terraform
terraform init -backend=false
cd ../..
bash infrastructure/scripts/deploy.sh \
  --project-id flighttracker-505314 \
  --skip-api-build
```

`deploy.sh` empaqueta funciones, corre `terraform plan` y bloquea `apply` si detecta drift. No se ejecuta `apply` durante la demostracion.

## 5. Batch BTS extremo a extremo y KPI en BigQuery

**Evidencia:** `09-batch-bts-extremo-a-extremo.md`, `01-bigquery-kpi.md`, `10-consistencia-id-vuelo.md`

```bash
bq query --use_legacy_sql=false '
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT flight_id) AS distinct_flight_ids,
  COUNTIF(flight_id IS NULL) AS null_flight_ids
FROM `flighttracker-505314.flighttracker_gold.fact_flights`;
'
```

Resultado esperado: 542.695 filas, 542.695 `flight_id` distintos, 0 nulos.

KPI de puntualidad (top 10 rutas):

```sql
SELECT
  da.iata_code AS airline,
  ao_airport.iata_code AS origin_iata,
  ad_airport.iata_code AS dest_iata,
  ao.total_flights,
  ao.on_time_flights,
  ROUND(ao.on_time_percentage, 2) AS on_time_percentage,
  ROUND(ao.avg_arr_delay, 2) AS avg_arr_delay
FROM `flighttracker-505314.flighttracker_gold.agg_on_time_performance` ao
LEFT JOIN `flighttracker-505314.flighttracker_gold.dim_airline` da
  ON ao.airline_key = da.airline_key
LEFT JOIN `flighttracker-505314.flighttracker_gold.dim_airport` ao_airport
  ON ao.origin_key = ao_airport.airport_key
LEFT JOIN `flighttracker-505314.flighttracker_gold.dim_airport` ad_airport
  ON ao.dest_key = ad_airport.airport_key
WHERE ao.total_flights >= 100
ORDER BY on_time_percentage DESC, total_flights DESC
LIMIT 10;
```

**Contexto de la cifra:** `fact_flights` llego a tener 4.895.569 filas con solo 518.677 `flight_id` distintos (89,41% de duplicacion), causado por una lectura con comodin sobre RAW que sumaba nueve copias del dataset. Se corrigio restringiendo la lectura al archivo canonico y reconstruyendo `build_flight_id()`. La cifra de 4.895.569 no se presenta como KPI valido; es el diagnostico del problema ya corregido, documentado en `docs/sprint1/evidencias/09-batch-bts-extremo-a-extremo.md`.

## 6. Serving batch por API

**Evidencia:** `02-firestore-serving-normalization.md`

```bash
curl -sS "https://get-flights-api-310107974919.us-central1.run.app/flights?limit=5"
```

La API lee de Firestore `flights_v1` con campos normalizados. Se usan los campos canonicos en minuscula; los alias legacy se mantienen solo por compatibilidad.

## 7. Validacion integral (`validate.sh`)

**Evidencia:** `07-validation-workflow-pass.md`

En un clon nuevo o una sesion nueva de Cloud Shell, `terraform init -backend=false` debe ejecutarse antes de este paso (ver `README.md`).

```bash
bash infrastructure/scripts/validate.sh \
  --project-id flighttracker-505314
```

Resultado esperado: 10 de 10 chequeos en verde (`terraform validate`, `api health`, `api flights`, `api live flights`, `pubsub topic exists`, `firestore collection probe`, `bigquery gold fact rows`, `latest dataproc job visible`, `scheduler job exists`, `dq report presence`).

## 8. Rama live: esqueleto OpenSky

**Evidencia:** `03-validacion-skeleton-opensky.md`, `12-diagnostico-conectividad-opensky.md`

```bash
curl -sS "https://get-flights-api-310107974919.us-central1.run.app/live/flights/abc123"
```

El esqueleto live esta desplegado y validado extremo a extremo: productor en Cloud Run, topico dedicado (`opensky-states-v1`), funcion de proyeccion, coleccion `live_flights` y endpoints `/live/*`. Se muestra el evento de prueba `icao24=abc123` como verificacion del pipeline.

La conectividad activa hacia OpenSky desde Google Cloud no esta confirmada: la conexion directa por `curl` no se establece, y los logs del servicio productor desplegado no muestran llamadas exitosas a OpenSky en la ventana revisada. El detalle completo del diagnostico, incluyendo el hallazgo de que el servicio desplegado ejecuta una version no versionada del codigo, esta en `docs/sprint1/evidencias/12-diagnostico-conectividad-opensky.md`. Resolver esta conectividad es el primer item del backlog de Sprint 2.

El endpoint `/live/count` esta limitado a 500 por implementacion (`list_live_flights(500)` en `backend/api/get_flights/main.py`); no refleja un conteo real de la coleccion.

## 9. Calidad de datos

**Evidencia:** `docs/sprint1/data-assessment/results/dq_summary.csv`

| Dataset | `row_count` | Completitud | `dq_score` |
|---|---|---|---|
| `bts` | 544.003 | 0,9083 | 0,9725 |
| `openflights_airlines` | 6.162 | 0,2493 | 0,7195 |
| `openflights_airports` | 7.698 | 1,0 | 0,9999 |
| `opensky` | 0 | - | 1,0 |

El `dq_score` de 0,7195 en `airlines` se explica por una completitud de 24,93% en la fuente de origen: es una limitacion del dataset, no del pipeline. El `dq_score` de 1,0 en `opensky` corresponde a `row_count = 0` y no representa calidad perfecta; es consecuencia directa de la restriccion de conectividad descrita en la seccion 8.

## 10. Reproducibilidad y guardrails de destruccion

**Evidencia:** `08-destroy-workflow-guardrails.md`, `11-input-productivo-sin-archivos-prueba.md`

```bash
bash infrastructure/scripts/destroy.sh --help
```

`destroy.sh` documenta guardrails: rechazo de `prod` sin `--allow-prod`, preservacion del backend remoto por defecto. No se ejecuta durante la demostracion.

El input productivo del batch es exclusivamente `bts_flights_corregido.csv`. Los archivos `test_*` y la muestra presentes en RAW no participan del resultado mostrado.

## 11. Limitaciones declaradas

- **CI/CD:** no implementado en Sprint 1.
- **Monitoreo y alertas:** no implementados. El logging operativo si existe, via servicios nativos de Google Cloud Platform.
- **Gobernanza - bucket:** `flighttracker-raw-bts` usaba roles legacy (`legacyBucketOwner`) que no otorgaban lectura de objetos pese al rol de editor a nivel de proyecto. Corregido durante el sprint; la migracion a control de acceso uniforme queda para Sprint 2.
- **Seguridad - credencial:** una contrasena de Cloud SQL quedo como valor por defecto en el historial de un repositorio publico. Se trato como comprometida: rotacion aplicada en la instancia, migracion a Secret Manager, `authorizedNetworks` depurado, `sslMode = ENCRYPTED_ONLY`, valor por defecto eliminado del codigo. Se decidio no reescribir el historial de Git: tras la rotacion el literal no da acceso a nada, y reescribir el historial de un repositorio publico compartido por el equipo tiene alto riesgo operativo para un beneficio nulo.

## 12. Backlog de Sprint 2

1. Resolver la conectividad real hacia OpenSky desde Google Cloud.
2. Comitear o retirar el mecanismo de respaldo no versionado que corre actualmente en `opensky-producer` desplegado, para que el codigo del repositorio refleje lo que esta en produccion.
3. Corregir `/live/count` para que refleje un conteo real de la coleccion.
4. Cerrar el drift de Terraform conocido (movimiento regional de `validate_and_persist_bts`).
5. Migrar `flighttracker-raw-bts` a control de acceso uniforme con roles IAM explicitos.
6. Perfilar OpenSky sobre volumen real, una vez resuelta la conectividad.
