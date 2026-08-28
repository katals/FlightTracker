import os

from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import (
    broadcast,
    coalesce,
    col,
    concat,
    date_format,
    dayofmonth,
    dayofweek,
    explode,
    expr,
    lit,
    month,
    row_number,
    sequence,
    sha2,
    to_date,
    trim,
    upper,
    when,
    year,
)
from pyspark.sql.types import IntegerType


PROJECT_ID = os.environ.get("PROJECT_ID", "flighttracker-505314")
BUCKET_CURATED = os.environ.get("BUCKET_CURATED", "flighttracker-curated-bts")
SILVER_PATH = os.environ.get(
    "SILVER_PATH", f"gs://{BUCKET_CURATED}/silver/bts_flights"
)
BIGQUERY_DATASET = os.environ.get("BIGQUERY_DATASET", "flighttracker_gold")
OPENFLIGHTS_PATH = os.environ.get(
    "OPENFLIGHTS_PATH", "gs://flighttracker-scripts/openflights"
)
TEMP_BUCKET = os.environ.get(
    "TEMP_BUCKET", "dataproc-temp-us-east1-310107974919-cz7rmf4e"
)

print("=== Iniciando ETL de Gold (modelo en estrella) ===")
print(f"Leyendo Silver desde: {SILVER_PATH}")

spark = (
    SparkSession.builder.appName("Gold_ETL_v6")
    .config("spark.sql.adaptive.enabled", "true")
    .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
    .config("spark.hadoop.google.cloud.auth.serviceAccount.enable", "true")
    .getOrCreate()
)


def canonical_string(column):
    return trim(coalesce(column.cast("string"), lit("")))


def canonical_upper(column):
    return upper(canonical_string(column))


def canonical_dep_time(column):
    # Alinea el hash analitico con el contrato operacional para que
    # 930.0 y 930 produzcan el mismo identificador.
    return coalesce(column.cast(IntegerType()).cast("string"), lit(""))


def build_flight_id(df):
    business_identity = concat(
        date_format(col("FL_DATE"), "yyyy-MM-dd"),
        lit("|"),
        canonical_upper(col("OP_CARRIER")),
        lit("|"),
        canonical_string(col("OP_CARRIER_FL_NUM")),
        lit("|"),
        canonical_upper(col("ORIGIN")),
        lit("|"),
        canonical_upper(col("DEST")),
        lit("|"),
        canonical_dep_time(col("DEP_TIME")),
    )
    return df.withColumn("flight_id", sha2(business_identity, 256))


def dedupe_airlines(df):
    ranked = (
        df.withColumn("iata_code", canonical_upper(col("iata_code")))
        .withColumn("id_int", col("id").cast(IntegerType()))
        .withColumn(
            "active_rank",
            when(canonical_upper(col("active")) == lit("Y"), lit(1)).otherwise(lit(0)),
        )
    )
    window = Window.partitionBy("iata_code").orderBy(
        col("active_rank").desc(),
        col("id_int").asc_nulls_last(),
        col("name").asc_nulls_last(),
    )
    deduped = ranked.withColumn("row_num", row_number().over(window)).filter(
        col("row_num") == 1
    )
    key_window = Window.orderBy("iata_code", "id_int")
    return (
        deduped.drop("row_num")
        .withColumn("airline_key", row_number().over(key_window))
        .drop("active_rank")
    )


def dedupe_airports(df):
    ranked = (
        df.withColumn("iata_code", canonical_upper(col("iata_code")))
        .withColumn("id_int", col("id").cast(IntegerType()))
    )
    window = Window.partitionBy("iata_code").orderBy(
        col("id_int").asc_nulls_last(),
        col("name").asc_nulls_last(),
    )
    deduped = ranked.withColumn("row_num", row_number().over(window)).filter(
        col("row_num") == 1
    )
    key_window = Window.orderBy("iata_code", "id_int")
    return deduped.drop("row_num").withColumn(
        "airport_key", row_number().over(key_window)
    )


# 1. Leer Silver
silver_df = spark.read.parquet(SILVER_PATH)
silver_count = silver_df.count()
print(f"Registros en Silver: {silver_count}")

# 2. Generar flight_id canónico y no nulo usando el mismo contrato operacional
silver_df = build_flight_id(silver_df)
null_flight_ids = silver_df.filter(col("flight_id").isNull()).count()
distinct_flight_ids = silver_df.select("flight_id").distinct().count()
print(f"flight_id distintos en Silver: {distinct_flight_ids}")
print(f"flight_id nulos en Silver: {null_flight_ids}")

# 3. Leer archivos de OpenFlights desde GCS
print("Leyendo archivos de OpenFlights desde GCS...")
airlines_path = f"{OPENFLIGHTS_PATH}/airlines.dat"
airports_path = f"{OPENFLIGHTS_PATH}/airports.dat"

airlines_raw = (
    spark.read.option("header", "false")
    .csv(airlines_path)
    .select(
        col("_c0").alias("id"),
        col("_c1").alias("name"),
        col("_c2").alias("alias"),
        col("_c3").alias("iata_code"),
        col("_c4").alias("icao_code"),
        col("_c5").alias("callsign"),
        col("_c6").alias("country"),
        col("_c7").alias("active"),
    )
    .filter(col("iata_code").isNotNull())
    .filter(trim(col("iata_code")) != "")
)

airports_raw = (
    spark.read.option("header", "false")
    .csv(airports_path)
    .select(
        col("_c0").alias("id"),
        col("_c1").alias("name"),
        col("_c2").alias("city"),
        col("_c3").alias("country"),
        col("_c4").alias("iata_code"),
        col("_c5").alias("icao_code"),
        col("_c6").alias("latitude"),
        col("_c7").alias("longitude"),
        col("_c8").alias("altitude"),
    )
    .filter(col("iata_code").isNotNull())
    .filter(trim(col("iata_code")) != "")
)

print(f"Aerolíneas OpenFlights leídas: {airlines_raw.count()}")
print(f"Aeropuertos OpenFlights leídos: {airports_raw.count()}")

# 4. Dimensiones deduplicadas por IATA con claves surrogate determinísticas
airlines_dim = dedupe_airlines(airlines_raw)
airports_dim = dedupe_airports(airports_raw)

print(f"dim_airline deduplicada: {airlines_dim.count()} filas")
print(f"dim_airport deduplicada: {airports_dim.count()} filas")

airline_lookup = broadcast(airlines_dim.select("airline_key", "iata_code"))
origin_lookup = broadcast(airports_dim.select("airport_key", "iata_code").alias("origin"))
dest_lookup = broadcast(airports_dim.select("airport_key", "iata_code").alias("dest"))

# 5. dim_date con secuencia real de fechas
date_bounds = silver_df.selectExpr(
    "min(FL_DATE) as min_date", "max(FL_DATE) as max_date"
).first()
print(f"Rango de fechas: {date_bounds['min_date']} - {date_bounds['max_date']}")

date_range = (
    spark.createDataFrame([(date_bounds["min_date"], date_bounds["max_date"])], ["min_date", "max_date"])
    .select(explode(sequence(col("min_date"), col("max_date"))).alias("full_date"))
    .withColumn("date_key", date_format(col("full_date"), "yyyyMMdd").cast(IntegerType()))
    .withColumn("year", year(col("full_date")))
    .withColumn("month", month(col("full_date")))
    .withColumn("day", dayofmonth(col("full_date")))
    .withColumn("day_of_week", dayofweek(col("full_date")))
    .withColumn(
        "is_weekend",
        when((col("day_of_week") == 1) | (col("day_of_week") == 7), True).otherwise(False),
    )
    .withColumn("quarter", expr("quarter(full_date)"))
    .withColumn("day_name", date_format(col("full_date"), "EEEE"))
)

# 6. Fact table
fact_df = (
    silver_df.alias("silver")
    .join(
        airline_lookup.alias("airline"),
        canonical_upper(col("silver.OP_CARRIER")) == col("airline.iata_code"),
        "left",
    )
    .join(
        origin_lookup,
        canonical_upper(col("silver.ORIGIN")) == col("origin.iata_code"),
        "left",
    )
    .join(
        dest_lookup,
        canonical_upper(col("silver.DEST")) == col("dest.iata_code"),
        "left",
    )
    .withColumn("date_key", date_format(col("silver.FL_DATE"), "yyyyMMdd").cast(IntegerType()))
    .select(
        col("silver.flight_id").alias("flight_id"),
        col("date_key"),
        col("airline.airline_key").alias("airline_key"),
        col("origin.airport_key").alias("origin_key"),
        col("dest.airport_key").alias("dest_key"),
        col("silver.DEP_DELAY").cast(IntegerType()).alias("dep_delay"),
        col("silver.ARR_DELAY").cast(IntegerType()).alias("arr_delay"),
        col("silver.CANCELLED").alias("cancelled"),
        col("silver.AIR_TIME").cast(IntegerType()).alias("air_time"),
        col("silver.DISTANCE").cast(IntegerType()).alias("distance"),
        col("silver.DEP_TIME").cast(IntegerType()).alias("dep_time"),
        col("silver.ARR_TIME").cast(IntegerType()).alias("arr_time"),
    )
)

print("Fact table preparada para escritura en BigQuery")

# 7. Escribir en BigQuery con bucket temporal
bigquery_output = f"{PROJECT_ID}:{BIGQUERY_DATASET}"
write_options = {"temporaryGcsBucket": TEMP_BUCKET}

(
    airlines_dim.select("airline_key", "iata_code", "icao_code", "name", "country")
    .write.format("bigquery")
    .options(**write_options)
    .option("table", f"{bigquery_output}.dim_airline")
    .mode("overwrite")
    .save()
)

(
    airports_dim.select(
        "airport_key",
        "iata_code",
        "icao_code",
        "name",
        "city",
        "country",
        "latitude",
        "longitude",
        "altitude",
    )
    .write.format("bigquery")
    .options(**write_options)
    .option("table", f"{bigquery_output}.dim_airport")
    .mode("overwrite")
    .save()
)

(
    date_range.write.format("bigquery")
    .options(**write_options)
    .option("table", f"{bigquery_output}.dim_date")
    .mode("overwrite")
    .save()
)

(
    fact_df.write.format("bigquery")
    .options(**write_options)
    .option("table", f"{bigquery_output}.fact_flights")
    .mode("overwrite")
    .save()
)

print("Tablas base guardadas en BigQuery")

# 8. Tablas agregadas
on_time_df = (
    fact_df.filter(col("cancelled") == False)
    .withColumn("is_on_time", when(col("arr_delay") <= 15, 1).otherwise(0))
    .groupBy("airline_key", "origin_key", "dest_key")
    .agg(
        expr("count(*) as total_flights"),
        expr("sum(is_on_time) as on_time_flights"),
        expr("avg(arr_delay) as avg_arr_delay"),
    )
    .withColumn(
        "on_time_percentage",
        col("on_time_flights") / col("total_flights") * 100,
    )
)

(
    on_time_df.write.format("bigquery")
    .options(**write_options)
    .option("table", f"{bigquery_output}.agg_on_time_performance")
    .mode("overwrite")
    .save()
)

delay_dist_df = (
    fact_df.filter(col("cancelled") == False)
    .filter(col("dep_time").isNotNull())
    .withColumn("hour_of_day", expr("floor(dep_time / 100)"))
    .withColumn("date_as_date", to_date(col("date_key").cast("string"), "yyyyMMdd"))
    .withColumn("day_of_week", dayofweek(col("date_as_date")))
    .groupBy("airline_key", "hour_of_day", "day_of_week")
    .agg(
        expr("avg(dep_delay) as avg_dep_delay"),
        expr("avg(arr_delay) as avg_arr_delay"),
        expr("count(*) as count"),
    )
)

(
    delay_dist_df.write.format("bigquery")
    .options(**write_options)
    .option("table", f"{bigquery_output}.agg_delay_distribution")
    .mode("overwrite")
    .save()
)

print("Tablas agregadas creadas")
spark.stop()
