# ADR-002: Alcance validado de Sprint 1

## Estado

Aprobado para Sprint 1.

## Fecha

2026-08-25

## Decision

La comunicacion tecnica y funcional del proyecto se basara en el alcance efectivamente validado en Sprint 1.

Ese alcance incluye:

- batch BTS limpio con salida Silver en Parquet
- capa Gold corregida en BigQuery
- API operativa en Cloud Run
- serving de Sprint 1 en Firestore para batch y live
- orquestacion diaria mediante Cloud Scheduler, Cloud Function y Dataproc
- topologia operativa distribuida entre `us-central1` y `us-east1`

## Criterios de comunicacion

### 1. El repo describe estado validado

- la documentacion del sprint se centra en lo que fue ejecutado, medido y guardado como evidencia
- los diagramas del repo representan servicios, flujos y contratos usados en la entrega

### 2. La capa analitica y la capa operacional se comunican por su rol real

- Silver es la fuente limpia del batch
- BigQuery Gold es la capa analitica consultable
- Firestore soporta el serving utilizado en la entrega

### 3. La reproduccion documentada se comunica por alcance validado

- `bootstrap.sh` prepara prerrequisitos
- `deploy.sh` valida el workflow de empaquetado y plan controlado
- `validate.sh` confirma la operacion observable del sprint
- `destroy.sh` documenta un workflow seguro de destruccion controlada

### 4. La topologia regional se comunica tal como opera

- datos, API y serving principal en `us-central1`
- orquestacion batch y Dataproc en `us-east1`

## Resultado

El repositorio, el README y las evidencias describen Sprint 1 como un walking skeleton validado con:

- batch productivo demostrable
- KPI consultable sobre BigQuery
- contratos canonicos de datos
- API y serving operativos
- scripts reproducibles de soporte

## Referencias

- `docs/decisiones/ADR-001-almacen-canonico-vuelos-y-contrato-de-proyeccion.md`
- `docs/sprint1/evidencias/06-terraform-plan-clean.md`
- `docs/sprint1/evidencias/07-validation-workflow-pass.md`
