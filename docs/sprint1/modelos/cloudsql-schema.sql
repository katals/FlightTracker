CREATE TABLE IF NOT EXISTS airlines (
    iata_code CHAR(2) PRIMARY KEY,
    icao_code CHAR(3),
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50)
);

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
