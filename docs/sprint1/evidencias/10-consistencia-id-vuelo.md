# Evidencia 10 - Consistencia de `flight_id`

**Fecha:** 2026-08-25  
**Punto del plan:** ``flight_id` es canonico, no nulo y consistente entre operacional y analitico`

## Problema corregido

La reconstruccion de Gold podia divergir del contrato operacional al construir `flight_id` usando `DEP_TIME` como texto crudo. Eso podia generar hashes distintos para el mismo vuelo cuando el valor aparecia como `930.0` en una rama y `930` en otra.

## Cambio aplicado

Se ajusto `pipelines/batch/spark_jobs/etl_gold_modelo_estrella.py` para que el hash de Gold normalice `DEP_TIME` igual que la rama operacional:

- convertir `DEP_TIME` a entero
- convertir luego ese entero a `string`
- hashear la misma identidad de negocio documentada en ADR-001

## Evidencia de reconstruccion de Gold

Durante el rebuild corregido, el job reporto:

```text
Registros en Silver: 542695
flight_id distintos en Silver: 542695
flight_id nulos en Silver: 0
```

Y el job finalizo en estado `DONE` reescribiendo `fact_flights` y las tablas derivadas en BigQuery.

## Evidencia en BigQuery

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

## Evidencia del hash canonico esperado

Comando ejecutado:

```bash
python3 - <<'PY'
import hashlib

business_identity = "2026-01-15|AA|1234|MIA|JFK|930"
print("business_identity=", business_identity)
print("expected_flight_id=", hashlib.sha256(business_identity.encode("utf-8")).hexdigest())
PY
```

Salida observada:

```text
business_identity= 2026-01-15|AA|1234|MIA|JFK|930
expected_flight_id= 272f5d9c5a91351f07b985b5e8eabdbae4de664b5919fc38d484f6013f292e29
```

## Evidencia operacional

Comando ejecutado:

```bash
curl -sS "https://get-flights-api-310107974919.us-central1.run.app/flights?limit=1"
```

Respuesta observada:

```json
{
  "status": "success",
  "count": 1,
  "data": [
    {
      "flight_id": "272f5d9c5a91351f07b985b5e8eabdbae4de664b5919fc38d484f6013f292e29",
      "carrier": "AA",
      "flight_number": "1234",
      "origin": "MIA",
      "destination": "JFK",
      "dep_time": 930,
      "event_id": "manual-bts-002"
    }
  ]
}
```

## Conclusiones

- `flight_id` en Gold quedo sin nulos
- `flight_id` en Gold quedo con unicidad completa para la tabla de hechos actual
- el hash canonico esperado coincide con el `flight_id` visible en la rama operacional
- la rama operacional y la rama analitica quedan alineadas con el mismo contrato logico para Sprint 1

## Estado

**Completado** para Sprint 1.
