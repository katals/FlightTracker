# Runbook de reconstrucción — proyecto `flighttracker-506923`

**Fecha:** 2026-08-29
**Contexto:** el proyecto `flighttracker-505314` quedó sin billing y sin acceso. No hay
migración posible: se reconstruye desde cero. El repo de trabajo es
`https://github.com/katals/FlightTracker`.

Este runbook asume la regla de trabajo del equipo: **los comandos de GCP los ejecuta una
persona**, se revisa la salida y solo después se avanza al siguiente paso.

---

## 0. Bloqueos que hay que entender antes de correr nada

Estos tres puntos son la razón por la que `terraform apply` no habría funcionado tal cual
estaba el repo:

1. **Los nombres de bucket de GCS son globales.** `flighttracker-raw-bts`,
   `flighttracker-curated-bts`, `flighttracker-scripts` y el bucket de tfstate siguen
   existiendo en el proyecto viejo. Aunque el billing esté cerrado, los nombres siguen
   ocupados y el apply falla con 409. Por eso todo lleva el sufijo `-506923`.
2. **La service account de las funciones estaba clavada al número del proyecto viejo**
   (`310107974919-compute@developer.gserviceaccount.com`). Ahora se deriva de
   `data.google_project.project.number`.
3. **Firestore, el dataset de BigQuery, Artifact Registry y el bucket de scripts nunca
   estuvieron en Terraform.** En el proyecto viejo se crearon a mano; por eso la
   "reproducibilidad total" nunca cerró. Ahora Firestore y BigQuery están en código, y
   Artifact Registry + el bucket de zips los crea `bootstrap.sh` (son prerrequisito del
   primer apply, no se pueden autogenerar dentro del mismo apply).

---

## 1. Secretos que necesita el pipeline

Se revisó todo el código. Los únicos secretos reales son dos:

| Secreto | Quién lo usa | Obligatorio |
|---|---|---|
| `cloudsql-postgres-password` | `seed_openflights.py` (`DB_PASS`) y la conexión a Cloud SQL | Sí, para poblar `airlines`/`airports` |
| Credenciales OpenSky (`OPENSKY_USERNAME` / `OPENSKY_PASSWORD`) | `productor_opensky` | No — el productor funciona anónimo, pero con cuota más baja |

No hay API keys, tokens ni service account keys en el repo. Terraform crea el *secreto*
`cloudsql-postgres-password`, pero **no la versión**: eso se hace a mano (paso 4).

---

## 2. Prerrequisitos del entorno

```bash
gcloud auth login
gcloud config set project flighttracker-506923
gcloud config get-value project
gcloud billing projects describe flighttracker-506923
```

El último comando debe mostrar `billingEnabled: true`. Si no, nada de lo demás sirve.

---

## 3. Bootstrap (APIs, bucket de estado, bucket de zips, Artifact Registry)

```bash
cd ~/FlightTracker
git pull origin main
bash infrastructure/scripts/bootstrap.sh \
  --project-id flighttracker-506923 \
  --skip-docker-check
```

Crea: APIs habilitadas, `gs://flighttracker-tfstate-506923`,
`gs://flighttracker-function-sources-506923`, repo de Artifact Registry
`flighttracker-functions` en `us-central1`.

**Firestore:** el `google_firestore_database` de Terraform crea la base `(default)` en
modo nativo. Si el proyecto ya tuviera una base creada por consola, hay que importarla en
vez de crearla:

```bash
gcloud firestore databases list --project=flighttracker-506923
```

Si la lista sale vacía, seguir normal. Si sale algo, avisar antes de aplicar.

---

## 4. Secreto de Cloud SQL

Después del primer apply existe el secreto pero no su versión. Crear la versión con una
contraseña nueva (no reusar la del proyecto viejo, que se trató como comprometida):

```bash
# Generar y guardar en Secret Manager
openssl rand -base64 24 | tr -d '\n' | \
  gcloud secrets versions add cloudsql-postgres-password \
  --project=flighttracker-506923 --data-file=-

# Fijar esa misma contraseña en el usuario postgres
gcloud sql users set-password postgres \
  --instance=flighttracker-db \
  --project=flighttracker-506923 \
  --password="$(gcloud secrets versions access latest \
      --secret=cloudsql-postgres-password --project=flighttracker-506923)"
```

---

## 5. Deploy (empaqueta funciones, construye imágenes, aplica Terraform)

Primero plan-only, para leer qué va a crear:

```bash
bash infrastructure/scripts/deploy.sh \
  --project-id flighttracker-506923
```

Revisar el plan. En un proyecto vacío debe salir todo como `create` y **cero** `destroy`.
Si aparece algún `destroy`, parar y revisar.

Luego el apply real:

```bash
bash infrastructure/scripts/deploy.sh \
  --project-id flighttracker-506923 \
  --apply
```

`deploy.sh` ahora también empaqueta `start_batch_pipeline` y
`proyectar_estado_opensky`, construye las dos imágenes (`get-flights-api` y
`opensky-producer`) y sube los jobs de Spark a
`gs://flighttracker-scripts-506923/` **después** del apply.

---

## 6. Repoblar datos

### 6.1 Maestros OpenFlights

```bash
curl -sSL -o /tmp/airports.dat https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat
curl -sSL -o /tmp/airlines.dat https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat
gcloud storage cp /tmp/airports.dat /tmp/airlines.dat \
  gs://flighttracker-scripts-506923/openflights/ --project=flighttracker-506923
```

### 6.2 CSV de BTS (enero 2026)

El archivo canónico es `bts_flights_corregido.csv` (545.003 filas, 55.78 MiB). Si alguien
del equipo lo tiene local, subirlo tal cual:

```bash
gcloud storage cp bts_flights_corregido.csv \
  gs://flighttracker-raw-bts-506923/bts/bts_flights_corregido.csv \
  --project=flighttracker-506923
```

**Ojo:** el `finalized` de ese objeto dispara Eventarc → `split_and_publish_bts` →
Pub/Sub → `validate_and_persist_bts` → Firestore. Es decir, la ingesta operacional
arranca sola con esta subida. Subir **una sola vez** y no dejar copias de prueba en RAW:
la duplicación del 89% de Sprint 1 vino exactamente de eso.

Si nadie conserva el CSV, hay que redescargarlo del BTS (On-Time Performance, enero 2026)
antes de este paso. **Verificar hoy quién lo tiene** — es el único insumo que no se puede
regenerar con un comando.

### 6.3 Batch analítico (Silver → Gold)

```bash
# Dispara el orquestador (crea cluster efímero y corre bts_etl)
curl -sS "$(gcloud functions describe start_batch_pipeline \
  --region=us-east1 --project=flighttracker-506923 --format='value(serviceConfig.uri)')"

# Seguir el job
gcloud dataproc jobs list --region=us-east1 --project=flighttracker-506923 --limit=5
```

El ETL Gold todavía no lo lanza el orquestador (en Sprint 1 se corría a mano). Cuando
`bts_etl` termine:

```bash
gcloud dataproc jobs submit pyspark \
  gs://flighttracker-scripts-506923/etl_gold_modelo_estrella.py \
  --cluster=bts-prod-active --region=us-east1 --project=flighttracker-506923 \
  --properties=spark.executorEnv.PROJECT_ID=flighttracker-506923
```

Meterlo en `start_batch_pipeline` es tarea de Sprint 2 (el timeout de 300s de la función
no alcanza para esperar los dos jobs; toca Workflows o Airflow).

### 6.4 Seed de Cloud SQL

```bash
export DB_HOST="$(gcloud sql instances describe flighttracker-db \
  --project=flighttracker-506923 --format='value(ipAddresses[0].ipAddress)')"
export DB_NAME=flighttracker DB_USER=postgres
export DB_PASS="$(gcloud secrets versions access latest \
  --secret=cloudsql-postgres-password --project=flighttracker-506923)"
python3 database/scripts/seed_openflights.py
```

Requiere que la IP desde donde se corre esté en `cloud_sql_authorized_networks`. Pasarla
por `-var` en vez de abrir la instancia al mundo.

---

## 7. Validación

```bash
bash infrastructure/scripts/validate.sh --project-id flighttracker-506923
```

Los 10 checks deben pasar. Los que más probablemente fallen en el primer intento:

- `firestore collection probe` — si falla, revisar que `validate_and_persist_bts` tenga
  `FIRESTORE_COLLECTION=flights_v1` (ahora va en Terraform, antes se ponía a mano).
- `bigquery gold fact rows` — falla hasta que corra el ETL Gold del paso 6.3.
- `api live flights` — falla mientras no haya nada en `live_flights`.

---

## 8. Cifra de control

Cuando la reconstrucción esté bien, `fact_flights` debe volver a dar exactamente:

```sql
SELECT COUNT(*) total, COUNT(DISTINCT flight_id) unicos,
       COUNTIF(flight_id IS NULL) nulos
FROM `flighttracker-506923.flighttracker_gold.fact_flights`;
-- esperado: 542695 / 542695 / 0
```

Y el `flight_id` de la identidad `2026-01-15|AA|1234|MIA|JFK|930` debe seguir siendo
`272f5d9c5a91351f07b985b5e8eabdbae4de664b5919fc38d484f6013f292e29`. Si esos dos números
coinciden, la reconstrucción es equivalente a lo entregado en Sprint 1.
