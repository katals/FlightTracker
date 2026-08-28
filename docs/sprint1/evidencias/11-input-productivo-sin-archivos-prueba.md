# Evidencia 11 - Input productivo sin archivos `test_*`

**Fecha:** 2026-08-25  
**Punto del plan:** `No se usan archivos test_* como evidencia del producto final`

## Problema que habia que cerrar

En RAW siguen existiendo archivos de prueba, validacion, idempotencia y sample. Eso podia generar dos riesgos:

- contaminar el pipeline batch si el ETL seguia leyendo con wildcard
- presentar evidencia construida sobre archivos de prueba en lugar del input productivo real

## Evidencia en codigo

Comando ejecutado:

```bash
grep -n 'DEFAULT_INPUT_OBJECT\|BTS_INPUT_PATH\|INPUT_PATH' pipelines/batch/spark_jobs/bts_etl.py
```

Salida observada:

```text
10:DEFAULT_INPUT_OBJECT = "bts/bts_flights_corregido.csv"
12:INPUT_PATH = os.environ.get("BTS_INPUT_PATH", f"gs://{BUCKET_RAW}/{DEFAULT_INPUT_OBJECT}")
17:print(f"Leyendo desde: {INPUT_PATH}")
29:    .csv(INPUT_PATH)
```

## Evidencia en el bucket RAW

Comando ejecutado:

```bash
gcloud storage ls gs://flighttracker-raw-bts/bts/
```

Salida observada:

```text
gs://flighttracker-raw-bts/bts/bts_flights_corregido.csv
gs://flighttracker-raw-bts/bts/bts_sample_1000_corregido.csv
gs://flighttracker-raw-bts/bts/test_20260819.csv
gs://flighttracker-raw-bts/bts/test_20260819_233952.csv
gs://flighttracker-raw-bts/bts/test_20260819_235335.csv
gs://flighttracker-raw-bts/bts/test_20260819_v2.csv
gs://flighttracker-raw-bts/bts/test_idempotency_20260820_003116.csv
gs://flighttracker-raw-bts/bts/test_idempotency_20260820_004045.csv
gs://flighttracker-raw-bts/bts/test_validation_20260820_002902.csv
gs://flighttracker-raw-bts/bts/test_validation_20260820_003700.csv
```

## Conclusiones

- el producto final de Sprint 1 usa `bts_flights_corregido.csv` como input batch canonico
- los archivos `test_*` y el sample no participan en el input productivo

## Estado

**Completado** para Sprint 1.
