# Matriz de Preguntas de Negocio - Sprint 1

## Objetivo

Relacionar cada pregunta de negocio demostrada en Sprint 1 con su fuente, procesamiento, storage o serving y producto observable.

## Matriz

| Pregunta de negocio | Fuente principal | Procesamiento | Storage o serving | Producto demostrable |
|---|---|---|---|---|
| Que rutas y aerolineas muestran mejor puntualidad historica en enero de 2026 | BTS historico + OpenFlights | `bts_etl.py` limpia BTS y `etl_gold_modelo_estrella.py` calcula `agg_on_time_performance` | BigQuery `flighttracker_gold.agg_on_time_performance` + dimensiones | consulta KPI batch |
| Como se distribuyen los retrasos historicos del dataset limpio | BTS historico | `etl_gold_modelo_estrella.py` genera `agg_delay_distribution` desde Silver limpio | BigQuery `flighttracker_gold.agg_delay_distribution` | tabla agregada para analitica |
| Cuantos vuelos historicos validos quedaron luego de reconstruir Gold | BTS historico | limpieza de input BTS y reconstruccion de Silver y Gold | BigQuery `flighttracker_gold.fact_flights` | verificacion estructural del fact |
| Que vuelos batch puede consultar hoy un consumidor HTTP por fecha o aerolinea | BTS historico | `validate_and_persist_bts` normaliza y proyecta `flight.curated.v1` a `flights_v1` | Firestore `flights_v1` + Cloud Run `get-flights-api` | `GET /flights` y `GET /health` |
| Cual es el ultimo estado conocido disponible en la rama live | OpenSky publicado al flujo live | `project_opensky_state` normaliza por `icao24` y actualiza `live_flights` | Firestore `live_flights` + Cloud Run `get-flights-api` | `GET /live/flights`, `GET /live/flights/{icao24}`, `GET /live/count` |
| Cual es la calidad observada de las fuentes usadas en Sprint 1 | BTS limpio + OpenFlights + snapshot live exportado desde API | `generate_profiles.py` perfila y calcula metricas por dataset | `docs/sprint1/data-assessment/results/*` | `dq_summary.csv` y perfiles JSON |

## Referencias

- `docs/sprint1/evidencias/01-bigquery-kpi.md`
- `docs/sprint1/evidencias/02-firestore-serving-normalization.md`
- `docs/sprint1/evidencias/03-validacion-skeleton-opensky.md`
- `docs/sprint1/data-assessment/results/dq_summary.csv`
- `docs/sprint1/modelos/gold-star-schema.md`
- `docs/sprint1/modelos/serving-schema.md`
