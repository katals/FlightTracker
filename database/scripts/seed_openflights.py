import os

import pandas as pd
import psycopg2


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "flighttracker")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")


def require_env_secret(name: str, value: str | None) -> str:
    if value:
        return value
    raise RuntimeError(f"Missing required environment variable: {name}")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=require_env_secret("DB_PASS", DB_PASS),
    )


def create_tables(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS airlines (
            iata_code CHAR(2) PRIMARY KEY,
            icao_code CHAR(3),
            name VARCHAR(100) NOT NULL,
            country VARCHAR(50)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS airports (
            iata_code CHAR(3) PRIMARY KEY,
            icao_code CHAR(4),
            name VARCHAR(100) NOT NULL,
            city VARCHAR(50),
            country VARCHAR(50),
            latitude DECIMAL(10,6),
            longitude DECIMAL(10,6),
            altitude INTEGER
        );
        """
    )
    conn.commit()


def load_airlines(conn):
    url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
    df = pd.read_csv(url, header=None)
    df.columns = ["id", "name", "alias", "iata", "icao", "callsign", "country", "active"]

    df["iata"] = df["iata"].astype(str).str.strip().str[:2]
    df = df[df["iata"].str.match(r"^[A-Z]{2}$", na=False)]
    df = df.dropna(subset=["iata"])

    cur = conn.cursor()
    for _, row in df.iterrows():
        cur.execute(
            "INSERT INTO airlines (iata_code, icao_code, name, country) VALUES (%s, %s, %s, %s) ON CONFLICT (iata_code) DO NOTHING",
            (row["iata"], row["icao"], row["name"], row["country"]),
        )
    conn.commit()
    print(f"Airlines cargadas: {len(df)}")


def load_airports(conn):
    url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
    df = pd.read_csv(url, header=None)
    df.columns = [
        "id",
        "name",
        "city",
        "country",
        "iata",
        "icao",
        "lat",
        "lon",
        "alt",
        "timezone",
        "dst",
        "tz_db",
        "type",
        "source",
    ]

    df["iata"] = df["iata"].astype(str).str.strip()
    df = df[df["iata"].str.match(r"^[A-Z]{3}$", na=False)]
    df = df.dropna(subset=["iata"])

    cur = conn.cursor()
    for _, row in df.iterrows():
        cur.execute(
            "INSERT INTO airports (iata_code, icao_code, name, city, country, latitude, longitude, altitude) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (iata_code) DO NOTHING",
            (
                row["iata"],
                row["icao"],
                row["name"],
                row["city"],
                row["country"],
                row["lat"],
                row["lon"],
                row["alt"],
            ),
        )
    conn.commit()
    print(f"Aeropuertos cargados: {len(df)}")


if __name__ == "__main__":
    conn = get_connection()
    create_tables(conn)
    load_airlines(conn)
    load_airports(conn)
    conn.close()
