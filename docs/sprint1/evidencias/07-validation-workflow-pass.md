# Evidencia 07 - Validation workflow en verde

**Fecha:** 2026-08-25  
**Punto del plan:** `G3. validate.sh`

## Comando ejecutado en Cloud Shell

```bash
bash infrastructure/scripts/validate.sh \
  --project-id flighttracker-505314
```

## Resultado observado

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
[validate] Validation completed successfully with all checks passing.
```

## Conclusión

- `validate.sh` ya funciona como chequeo reproducible de Sprint 1
- los checks técnicos críticos quedaron validados en un solo comando
- la evidencia DQ ya está presente en `docs/sprint1/data-assessment/results`

## Estado

**Completado** para Sprint 1.
