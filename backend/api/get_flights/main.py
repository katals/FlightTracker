import os
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Query
from typing import Optional
# pyrefly: ignore [missing-import]
import uvicorn
from repository import FirestoreFlightRepository, FlightRepository

app = FastAPI(title="FlightTracker API", description="API para consultar vuelos procesados")

# La API depende de un puerto logico de lectura, no de un SDK especifico.
repository: FlightRepository = FirestoreFlightRepository()

@app.get("/flights")
async def get_flights(
    airline: Optional[str] = Query(None, description="Código IATA de la aerolínea (ej. AA)"),
    date: Optional[str] = Query(None, description="Fecha en formato YYYY-MM-DD"),
    limit: int = Query(100, description="Número máximo de resultados")
):
    """
    Endpoint para consultar vuelos filtrados por aerolínea y/o fecha.
    """
    try:
        results = repository.list_flights(airline, date, limit)
        return {"status": "success", "count": len(results), "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/live/flights")
async def get_live_flights(
    limit: int = Query(50, ge=1, le=500, description="Numero maximo de vuelos live")
):
    try:
        results = repository.list_live_flights(limit)
        return {"status": "success", "count": len(results), "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/live/flights/{icao24}")
async def get_live_flight(icao24: str):
    try:
        result = repository.get_live_flight(icao24)
        if result is None:
            return {"status": "error", "message": "Flight not found"}
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/live/count")
async def get_live_count():
    try:
        results = repository.list_live_flights(500)
        return {"status": "success", "count": len(results)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
