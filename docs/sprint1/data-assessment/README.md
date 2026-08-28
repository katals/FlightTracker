# Data Assessment - Sprint 1

Esta carpeta contiene el material reproducible de profiling y calidad de datos de Sprint 1.

## Archivos esperados

- `FlightTracker_Profiling.ipynb`
- `generate_profiles.py`
- `results/bts_profile.json`
- `results/openflights_airlines_profile.json`
- `results/openflights_airports_profile.json`
- `results/opensky_profile.json`
- `results/dq_summary.csv`

## Flujo reproducible en Cloud Shell

1. Descargar BTS productivo a un archivo local temporal.
2. Exportar un snapshot live desde la API a JSON.
3. Ejecutar `generate_profiles.py`.

El notebook puede usarse como guía, pero la ejecución automatizada queda en `generate_profiles.py`.
