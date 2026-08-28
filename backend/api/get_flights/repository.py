"""Puerto de persistencia para la API de lectura de FlightTracker."""

from typing import Optional, Protocol

from google.cloud import firestore
import os


class FlightRepository(Protocol):
    def list_flights(
        self, airline: Optional[str], flight_date: Optional[str], limit: int
    ) -> list[dict]:
        """Return flights using the canonical API filter names."""

    def list_live_flights(self, limit: int) -> list[dict]:
        """Return the latest live flight states."""

    def get_live_flight(self, icao24: str) -> Optional[dict]:
        """Return one live flight state by ICAO24."""


class FirestoreFlightRepository:
    """Implementacion del puerto de lectura usando Firestore."""

    def __init__(self) -> None:
        self._db = firestore.Client()
        self._flight_collection = os.environ.get("FIRESTORE_COLLECTION", "flights")

    def list_flights(
        self, airline: Optional[str], flight_date: Optional[str], limit: int
    ) -> list[dict]:
        query = self._db.collection(self._flight_collection)

        if airline:
            query = query.where(filter=firestore.FieldFilter("carrier", "==", airline.upper()))
        if flight_date:
            query = query.where(filter=firestore.FieldFilter("flight_date", "==", flight_date))

        return [document.to_dict() for document in query.limit(limit).stream()]

    def list_live_flights(self, limit: int) -> list[dict]:
        query = self._db.collection("live_flights")
        query = query.order_by("observed_at", direction=firestore.Query.DESCENDING)
        return [document.to_dict() for document in query.limit(limit).stream()]

    def get_live_flight(self, icao24: str) -> Optional[dict]:
        document = self._db.collection("live_flights").document(icao24.lower()).get()
        if not document.exists:
            return None
        return document.to_dict()
