# Evidencia 09 - Batch BTS extremo a extremo

**Fecha:** 2026-08-25  
**Punto del plan:** `BTS batch demostrable end-to-end`

## Alcance de esta evidencia

Para Sprint 1, el criterio valido de batch extremo a extremo es la rama analitica:

`BTS productivo -> RAW -> Spark -> Silver limpio -> Gold Star Schema -> BigQuery -> KPI validado`

## Evidencia operativa de ejecucion batch

Comando ejecutado:

```bash
gcloud dataproc jobs list \
  --region=us-east1 \
  --limit=5
```

Salida observada:

```text
JOB_ID: 719b11eb-2333-4f21-b78e-9bfc4382a07f
TYPE: pyspark
STATUS: DONE

JOB_ID: 88aba28f-0a93-4a9c-859d-913e6def6c10
TYPE: pyspark
STATUS: DONE

JOB_ID: 783192df-cb7f-47bd-b847-1554a423399f
TYPE: pyspark
STATUS: ERROR

JOB_ID: 0503365b-6273-462f-9d0a-7aebbc3caf5a
TYPE: pyspark
STATUS: DONE

JOB_ID: cd040bf3-f62d-4281-8b8f-3658509e48de
TYPE: pyspark
STATUS: ERROR
```

Interpretacion:

- existen ejecuciones recientes exitosas de `Dataproc`
- la cadena batch no depende de una sola corrida historica
- tambien hubo intentos previos no exitosos, lo cual forma parte del historial operativo del entorno

## Evidencia de salida Gold valida

Comando ejecutado:

```bash
bq query --use_legacy_sql=false '
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT flight_id) AS distinct_flight_ids,
  COUNTIF(flight_id IS NULL) AS null_flight_ids
FROM `flighttracker-505314.flighttracker_gold.fact_flights`;
'
```

Salida observada:

```text
+------------+---------------------+-----------------+
| total_rows | distinct_flight_ids | null_flight_ids |
+------------+---------------------+-----------------+
|     542695 |              542695 |               0 |
+------------+---------------------+-----------------+
```

## Evidencia de consumo analitico

La capa Gold ya tiene evidencia propia de consulta KPI en:

- `docs/sprint1/evidencias/01-bigquery-kpi.md`

## Nota sobre el serving batch

La API batch sigue operativa y el serving fue validado por separado en:

- `docs/sprint1/evidencias/02-firestore-serving-normalization.md`

## Conclusiones

- el batch productivo de Sprint 1 es demostrable de extremo a extremo en su rama analitica
- la evidencia valida para ese cierre es `Dataproc -> Gold limpio -> BigQuery -> KPI`
- el serving batch ya fue probado por separado y no se usa aqui como evidencia principal de la rama analitica

## Estado

**Completado** para Sprint 1.
