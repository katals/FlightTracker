import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, year, month, dayofmonth, split
from pyspark.sql.types import IntegerType, BooleanType

PROJECT_ID = os.environ.get("PROJECT_ID", "flighttracker-505314")
BUCKET_RAW = os.environ.get("BUCKET_RAW", "flighttracker-raw-bts")
BUCKET_CURATED = os.environ.get("BUCKET_CURATED", "flighttracker-curated-bts")
DEFAULT_INPUT_OBJECT = "bts/bts_flights_corregido.csv"
# Sprint 1 runs must ignore test and idempotency copies still present in RAW.
INPUT_PATH = os.environ.get("BTS_INPUT_PATH", f"gs://{BUCKET_RAW}/{DEFAULT_INPUT_OBJECT}")
OUTPUT_SILVER = f"gs://{BUCKET_CURATED}/silver/bts_flights"
OUTPUT_GOLD = f"gs://{BUCKET_CURATED}/gold/bts_flights"

print("=== Iniciando ETL de BTS ===")
print(f"Leyendo desde: {INPUT_PATH}")

spark = SparkSession.builder \
    .appName("BTS_ETL") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
    .getOrCreate()

# 1. Leer CSV
df = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .csv(INPUT_PATH)

total_rows = df.count()
print(f"1. Registros totales leídos: {total_rows}")
print(f"   Columnas: {df.columns}")

# BTS files can expose either OP_CARRIER or OP_UNIQUE_CARRIER. The pipeline
# keeps one canonical carrier field for Silver and downstream projections.
carrier_source = "OP_CARRIER" if "OP_CARRIER" in df.columns else "OP_UNIQUE_CARRIER"
if carrier_source not in df.columns:
    raise ValueError("BTS input is missing OP_CARRIER/OP_UNIQUE_CARRIER")
df = df.withColumn("OP_CARRIER", col(carrier_source))

# 2. Extraer solo la fecha (antes del espacio) y parsear con formato MM/dd/yyyy
df_date = df.withColumn("FL_DATE_STRING", split(col("FL_DATE"), " ").getItem(0)) \
    .withColumn("FL_DATE_PARSED", to_date(col("FL_DATE_STRING"), "MM/dd/yyyy"))

parsed_count = df_date.filter(col("FL_DATE_PARSED").isNotNull()).count()
print(f"2. Fechas parseadas correctamente: {parsed_count} de {total_rows}")
df = df_date

# 3. Filtros iniciales (eliminar nulos en columnas clave)
df_filtered = df \
    .filter(col("FL_DATE_PARSED").isNotNull()) \
    .filter(col("OP_CARRIER").isNotNull()) \
    .filter(col("ORIGIN").isNotNull()) \
    .filter(col("DEST").isNotNull())

print(f"3. Registros después de filtrar nulos: {df_filtered.count()}")

# 4. Capa Silver: limpieza y transformaciones. Cancelled flights retain null
# delay values: imputing zero would bias punctuality metrics.
silver_df = df_filtered \
    .withColumn("FL_DATE", col("FL_DATE_PARSED")) \
    .withColumn("CANCELLED", col("CANCELLED").cast(BooleanType())) \
    .filter(
        col("CANCELLED") |
        ((col("DEP_DELAY") >= -60) & (col("ARR_DELAY") >= -60))
    ) \
    .withColumn("YEAR", year(col("FL_DATE"))) \
    .withColumn("MONTH", month(col("FL_DATE"))) \
    .withColumn("DAY", dayofmonth(col("FL_DATE")))

print(f"4. Silver: registros después de limpieza y rango de retrasos: {silver_df.count()}")

# Guardar Silver (Parquet, particionado por año/mes)
silver_df.write \
    .mode("overwrite") \
    .partitionBy("YEAR", "MONTH") \
    .parquet(OUTPUT_SILVER)

print(f"✅ Silver guardado en: {OUTPUT_SILVER}")

# 5. Capa Gold: modelo en estrella (hechos y dimensiones)
gold_df = silver_df.select(
    col("FL_DATE").alias("fl_date"),
    col("OP_CARRIER").alias("airline_code"),
    col("OP_CARRIER_FL_NUM").alias("flight_number"),
    col("ORIGIN").alias("origin"),
    col("DEST").alias("dest"),
    col("DEP_TIME").cast(IntegerType()).alias("dep_time"),
    col("DEP_DELAY").cast(IntegerType()).alias("dep_delay"),
    col("ARR_TIME").cast(IntegerType()).alias("arr_time"),
    col("ARR_DELAY").cast(IntegerType()).alias("arr_delay"),
    col("CANCELLED").alias("cancelled"),
    col("AIR_TIME").cast(IntegerType()).alias("air_time"),
    col("DISTANCE").cast(IntegerType()).alias("distance"),
    col("YEAR"),
    col("MONTH"),
    col("DAY")
)

print(f"5. Gold: registros seleccionados: {gold_df.count()}")

gold_df.write \
    .mode("overwrite") \
    .partitionBy("YEAR", "MONTH") \
    .parquet(OUTPUT_GOLD)

print(f"✅ Gold guardado en: {OUTPUT_GOLD}")
spark.stop()
