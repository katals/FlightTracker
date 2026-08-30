# Traspaso — reconstrucción del entorno (sábado 29 de agosto de 2026)

**Autora:** Gabriela Martínez
**Proyecto GCP nuevo:** `flighttracker-506923`
**Repo:** `https://github.com/katals/FlightTracker`, rama `reconstruccion-506923`

---

## 1. Situación de partida

Agustín salió del equipo. El proyecto `flighttracker-505314` estaba en su cuenta
personal de estudiante y se quedó sin créditos: la cuenta de facturación quedó
cerrada. Ni él podía extraer nada. No hubo migración posible — se reconstruyó
todo desde cero en un proyecto nuevo.

Se evaluó relinkear la facturación del proyecto viejo a otra cuenta (es técnicamente
posible), pero se descartó como camino principal: aunque funcionara, mantiene la
dependencia de una cuenta ajena al equipo y no garantiza que los datos hayan
sobrevivido, porque GCS y Pub/Sub borran recursos pronto cuando la facturación se
deshabilita.

---

## 2. Qué quedó funcionando

Todo esto está operativo y verificado en `flighttracker-506923`:

| Componente | Estado |
|---|---|
| Infraestructura completa vía Terraform | Creada desde cero, 47 recursos |
| Ingesta batch BTS (GCS → Eventarc → Pub/Sub → Firestore) | 544.003 filas publicadas |
| API de serving (Cloud Run) | `https://get-flights-api-u5qt55joha-uc.a.run.app` |
| Capa Gold en BigQuery | 6 tablas cargadas |
| Cloud SQL + Secret Manager | Instancia arriba, contraseña rotada |
| Maestros OpenFlights en GCS | Cargados |
| `validate.sh` | **10/10 en verde** |

### Cifras de control

```
fact_flights: 542.695 filas | 542.695 flight_id únicos | 0 nulos
dim_airline: 1.121 | dim_airport: 6.073 | dim_date: 31 (2026-01-01 a 2026-01-31)
```

Son **idénticas** a las de Sprint 1. La reconstrucción es equivalente a lo entregado.

Nota sobre el hash canónico: el `flight_id`
`272f5d9c...f292e29` de la identidad `2026-01-15|AA|1234|MIA|JFK|930` **no existe
en `fact_flights`**, y no es un error. Se verificó contra el dataset: ese día no
hubo ningún vuelo AA MIA→JFK a las 9:30. Ese caso de Sprint 1 fue un evento
sintético publicado a mano para probar el contrato de identidad, no un vuelo real.
Si se quiere reproducir la prueba, hay que republicar ese evento manual.

---

## 3. Buckets y nombres nuevos

Los nombres de bucket de GCS son **globales** y los del proyecto viejo siguen
ocupados. Todo lleva sufijo `-506923`:

```
flighttracker-raw-bts-506923
flighttracker-curated-bts-506923
flighttracker-scripts-506923
flighttracker-function-sources-506923
flighttracker-tfstate-506923
```

---

## 4. El CSV de BTS

El input canónico (`bts_flights_corregido.csv`) se perdió con el proyecto viejo.
No se esperó a que Agustín lo enviara: se redescargó el crudo de TranStats
(On-Time Reporting Carrier, enero 2026) y se reconstruyó la transformación.

El crudo trae otros nombres de columna (`FlightDate`, `Reporting_Airline`,
`Dest`, `DepTime`) que el pipeline no entiende. El script
`pipelines/batch/scripts/preparar_bts_crudo.py` hace el mapeo al esquema esperado
y **deja documentada** esa conversión, que antes solo existía dentro del archivo.

Resultado: 544.003 filas leídas, 544.003 escritas, 0 descartadas — coincide exacto
con el `row_count` del `dq_summary.csv` de Sprint 1.

Ese archivo ya está en `gs://flighttracker-raw-bts-506923/bts/`. **No subir otra
copia**: el `finalized` del objeto dispara Eventarc y la duplicación del 89% de
Sprint 1 vino exactamente de tener varias copias en RAW.

---

## 5. Lo que antes era manual y ahora está en código

Esto responde directo a la observación del profesor sobre reproducibilidad parcial:

1. **Firestore** — nunca estuvo en Terraform, se creaba por consola. Ahora es
   `google_firestore_database`.
2. **Dataset de BigQuery** — igual. Ahora es `google_bigquery_dataset`.
3. **Bucket de scripts de Spark** — vivía fuera de Terraform. Ahora es un recurso.
4. **Service agents de Eventarc y Cloud Storage** — no existen en un proyecto
   nuevo hasta que se fuerzan. `bootstrap.sh` las crea.
5. **APIs Cloud Resource Manager y Service Usage** — Terraform no puede
   habilitarlas a sí mismo. `bootstrap.sh` las habilita.
6. **Artifact Registry y bucket de zips** — prerrequisitos del primer apply,
   creados por `bootstrap.sh`.
7. **Service account de las funciones** — estaba clavada al número del proyecto
   viejo. Ahora se deriva de `data.google_project.project.number`.
8. **`FIRESTORE_COLLECTION=flights_v1`** — se ponía a mano tras cada redeploy.
   Ahora va en Terraform.
9. **Drift de la suscripción push** — apuntaba a `us-east1` mientras la función
   vive en `us-central1`. Corregido, y la suscripción heredada arranca desactivada
   porque el trigger Eventarc ya crea la suya.

---

## 6. Hallazgos nuevos — deuda técnica para Sprint 2

Tres cosas que no se sabían antes de esta reconstrucción:

1. **Terraform no redespliega las Cloud Functions cuando cambia el código.**
   Referencia el zip por `bucket` + `object` con nombre fijo, así que un zip nuevo
   con el mismo nombre es "sin cambios" para Terraform. Se detectó al intentar
   cambiar el tipo de máquina del cluster en `start_batch_pipeline` y ver que
   seguía corriendo el código viejo.
   *Solución propuesta:* incluir el hash del zip en el nombre del objeto.
   **Probablemente esto explica por qué en Sprint 1 tanto ajuste terminaba
   haciéndose por consola.**

2. **Falta el conector de BigQuery para Spark.** El ETL Gold falla con
   `Failed to find data source: bigquery` si no se pasa
   `--jars=gs://spark-lib/bigquery/spark-bigquery-latest_2.12.jar`.
   No estaba documentado en ningún lado.

3. **El cluster está subdimensionado para el ETL Gold.** `e2-standard-2` con cero
   workers mata el driver por memoria al escribir `fact_flights` (hay varios
   `Window` sin partición). Funcionó con `e2-standard-4` y
   `spark.driver.memory=8g`.

Además: el check `api live flights` de `validate.sh` pasa aunque `live_flights`
esté vacía — solo valida que el endpoint responda. No distingue "hay datos" de
"el endpoint está arriba".

---

## 7. Lo que falta

### Bloqueante para la demo
- **Orquestación del ETL Gold.** `start_batch_pipeline` solo lanza `bts_etl`. El
  Gold se lanza a mano. El timeout de 300s de la función no alcanza para esperar
  los dos jobs: toca Workflows o Airflow.

### Pendientes heredados de Sprint 1
- **OpenSky**: sigue sin conectividad real desde Cloud Run. La infraestructura
  (topics, productor, proyector, endpoints) está desplegada, pero `live_flights`
  está vacía. Sigue siendo el pendiente principal.
- **CI/CD, monitoreo y alertas**: no implementados.
- **Catálogo de datos (OpenMetadata)**: pendiente.
- **Seed de Cloud SQL**: la instancia y el secreto están listos, falta correr
  `seed_openflights.py` (requiere agregar la IP de origen a
  `cloud_sql_authorized_networks`).

### Entrega académica
- Presentación actualizada, roles del equipo (ahora somos tres), validación por
  terceros, planeación de Sprint 2.
- Corregir en las slides: decían 545.003 filas de BTS; el número real es
  **544.003**, que es el que reporta el `dq_summary.csv`.

---

## 8. Cómo entrar al proyecto

```bash
git clone https://github.com/katals/FlightTracker.git
cd FlightTracker
git checkout reconstruccion-506923
gcloud config set project flighttracker-506923
```

**Terraform ya no viene en Cloud Shell.** Hay que instalarlo primero:

```bash
cd ~
TF_VERSION=$(curl -s https://checkpoint-api.hashicorp.com/v1/check/terraform \
  | grep -o '"current_version":"[^"]*"' | cut -d'"' -f4)
curl -sSLo /tmp/terraform.zip \
  "https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_amd64.zip"
mkdir -p ~/bin && unzip -o /tmp/terraform.zip -d ~/bin
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc && export PATH="$HOME/bin:$PATH"
terraform version
```

Verificar que todo sigue arriba:

```bash
bash infrastructure/scripts/validate.sh --project-id flighttracker-506923
```

El runbook completo de reconstrucción está en
`docs/sprint2/runbook-reconstruccion.md`.

---

## 9. Cuidado con los créditos

La facturación del proyecto nuevo corre por cuenta de Gabriela y tiene que durar
siete semanas. Reglas:

- **Borrar los clusters de Dataproc al terminar.** Nadie deja un cluster corriendo.
  ```bash
  gcloud dataproc clusters list --region=us-east1 --project=flighttracker-506923
  gcloud dataproc clusters delete <nombre> --region=us-east1 \
    --project=flighttracker-506923 --quiet
  ```
- Usar `--max-idle` al crear clusters manualmente.
- Cloud SQL está en `db-f1-micro` y corre 24/7. Si no se está usando, se puede
  parar.
