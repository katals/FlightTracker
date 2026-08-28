# Mapeo Tecnologico GCP - Sprint 1

## Objetivo

Documentar los servicios de GCP usados en la implementacion validada de Sprint 1.

## Diagrama

```mermaid
flowchart LR
    BTS[BTS CSV] --> VAS[Cloud Function validate_and_store_bts]
    VAS --> GCSRAW[Cloud Storage RAW]
    GCSRAW --> EA[Eventarc]
    EA --> SPLIT[Cloud Function split_and_publish_bts]
    SPLIT --> PSBTS[Pub/Sub bts-flights-rows]
    PSBTS --> PERSIST[Cloud Function validate_and_persist_bts]
    PERSIST --> FSB[Firestore flights_v1]

    SCH[Cloud Scheduler] --> ORCH[Cloud Function start_batch_pipeline]
    ORCH --> DP[Dataproc + Spark]
    GCSRAW --> DP
    DP --> GCSS[Cloud Storage Silver]
    DP --> BQ[BigQuery Gold]

    OS[OpenSky] --> CRP[Cloud Run opensky-producer]
    CRP --> PSOS[Pub/Sub opensky-states-v1]
    PSOS --> PROJ[Cloud Function project_opensky_state]
    PROJ --> FSL[Firestore live_flights]

    OF[OpenFlights] --> SQL[Cloud SQL PostgreSQL]
    SM[Secret Manager] -.-> SQL

    FSB --> API[Cloud Run get-flights-api]
    FSL --> API

    TF[Terraform + scripts] -.-> GCSRAW
    TF -.-> PSBTS
    TF -.-> ORCH
    TF -.-> API
    TF -.-> SQL
```

## Servicios documentados

- Cloud Storage RAW y Silver
- Eventarc
- Pub/Sub batch y live
- Cloud Functions de validacion, particion, proyeccion y orquestacion
- Dataproc para batch con Spark
- BigQuery como capa Gold
- Firestore para serving de Sprint 1
- Cloud Run para API y productor live
- Cloud SQL para maestros OpenFlights
- Secret Manager para la credencial de Cloud SQL
- Terraform y scripts de soporte
