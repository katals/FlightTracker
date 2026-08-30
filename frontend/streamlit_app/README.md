# FlightTracker Streamlit App

Aplicacion visual para consultar la salida live de FlightTracker desde la API:

```text
Pub/Sub opensky-states-v1 -> project_opensky_state -> Firestore live_flights -> API /live/flights -> Streamlit
```

## Requisitos

- Python 3.11 o superior
- Acceso a internet
- API desplegada en GCP:

```text
https://get-flights-api-u5qt55joha-uc.a.run.app/live/flights
```

## Ejecutar en Windows

Desde la raiz del repo:

```powershell
cd "C:\Users\JUAN SIMON\OneDrive - Universidad EAFIT\Universidad\SEPTIMO SEMESTRE 2026 - 2\Proyecto de Ingenieria de datos\proyecto\FlightTracker"
py -m venv C:\venvs\flighttracker
C:\venvs\flighttracker\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r frontend\streamlit_app\requirements.txt
streamlit run frontend\streamlit_app\app.py
```

Si PowerShell bloquea la activacion del entorno:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
C:\venvs\flighttracker\Scripts\Activate.ps1
```

Abrir la URL que muestra Streamlit, normalmente:

```text
http://localhost:8501
```

## Ejecutar en Cloud Shell

Desde la raiz del repo:

```bash
cd ~/FlightTracker
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r frontend/streamlit_app/requirements.txt
streamlit run frontend/streamlit_app/app.py --server.port 8080 --server.address 0.0.0.0
```

Luego abrir **Web Preview** en el puerto `8080`.

## Datos live de prueba

Si `/live/flights` responde con `count: 0`, la app abre correctamente pero no muestra puntos en el mapa.

Para validar el skeleton live con un evento sintetico:

```bash
PROJECT_ID=flighttracker-506923

gcloud pubsub topics publish opensky-states-v1 \
  --project="$PROJECT_ID" \
  --message="{\"schema_version\":\"opensky.state.v1\",\"event_id\":\"manual-demo-001\",\"observed_at\":$(date +%s),\"icao24\":\"abc123\",\"callsign\":\"DEMO123\",\"origin_country\":\"Colombia\",\"longitude\":-74.0721,\"latitude\":4.7110,\"baro_altitude\":30000,\"geo_altitude\":30500,\"on_ground\":false,\"velocity\":430,\"heading\":95,\"vertical_rate\":0,\"source\":\"manual-demo\"}"
```

Despues de 10 a 20 segundos:

```bash
curl -sS "https://get-flights-api-u5qt55joha-uc.a.run.app/live/flights?limit=5"
```

La app debe mostrar el vuelo `DEMO123` en el mapa y la tabla.

## Nota para demo

El evento `manual-demo` valida el pipeline live, pero no representa una conexion real a OpenSky. La conectividad real con OpenSky sigue registrada como pendiente tecnico.
