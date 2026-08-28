# Arquitectura de Referencia Final - FlightTracker

## Objetivo

Consolidar la arquitectura de referencia usada para describir el sistema validado en Sprint 1.

Este documento se complementa con:

- el mapeo tecnologico GCP
- el flujo implementado de Sprint 1
- la matriz de preguntas de negocio

## Relacion con Sprint 0

Sprint 0 definio cuatro compromisos estructurales que se mantienen en la solucion presentada:

1. integrar tres fuentes heterogeneas: BTS, OpenSky y OpenFlights
2. combinar batch historico y una rama live del mismo dominio
3. organizar el dato en capas tipo lakehouse
4. exponer productos de consumo analitico y operacional

## Problema que resuelve la plataforma

FlightTracker integra y organiza informacion de trafico aereo para:

- reducir fragmentacion entre fuentes
- mejorar trazabilidad de los datos
- habilitar consulta analitica historica
- exponer consulta operacional por API

## Principios de arquitectura

### 1. Separacion entre verdad analitica y serving

- Silver es la fuente limpia del batch
- Gold es la capa analitica consultable
- la proyeccion operacional sirve lectura rapida por API

### 2. Contratos canonicos de datos

- `event_id` y `flight_id` se definen por contrato
- la API se desacopla del motor de storage mediante repositorios logicos

### 3. Batch y live comparten dominio

- ambas ramas usan contratos y modelos alineados
- el batch prioriza reconstruccion y KPI
- la rama live prioriza ultimo estado conocido

### 4. Infraestructura validable

- Terraform y scripts operativos documentan el entorno usado en la entrega
- el estado observable del sprint se verifica con `validate.sh`

## Capas de la arquitectura

### Fuentes

- BTS
- OpenSky
- OpenFlights

### Ingesta y mensajeria

- Cloud Storage RAW
- Pub/Sub
- funciones de validacion, particion y proyeccion

### Procesamiento

- Dataproc y Spark para batch
- productor y proyector live para OpenSky

### Curacion y analitica

- Silver en Parquet
- Gold en BigQuery con hechos, dimensiones y agregados KPI

### Serving y consumo

- Firestore para colecciones operativas usadas en Sprint 1
- Cloud Run `get-flights-api`

### Operacion y control

- Cloud Scheduler para orquestacion diaria
- Terraform y scripts de soporte
- profiling y DQ reproducibles

## Estado validado en Sprint 1

- input BTS limpio
- Silver limpio en Parquet
- Gold corregido en BigQuery
- Cloud SQL para maestros OpenFlights
- serving batch en `flights_v1`
- serving live en `live_flights`
- API `/health`, `/flights` y `/live/*`
- orquestacion diaria de batch

## Referencias

- `docs/decisiones/ADR-001-almacen-canonico-vuelos-y-contrato-de-proyeccion.md`
- `docs/decisiones/ADR-002-alcance-validado-sprint1.md`
- `docs/sprint1/arquitectura/mapeo-preguntas-negocio.md`
- `docs/sprint1/modelos/physical.md`
- `docs/sprint1/modelos/gold-star-schema.md`
- `docs/sprint1/modelos/serving-schema.md`
