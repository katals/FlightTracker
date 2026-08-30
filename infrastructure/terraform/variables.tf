variable "project_id" {
  description = "ID del proyecto GCP"
  type        = string
}

variable "bucket_suffix" {
  description = "Sufijo unico para nombres de bucket. Los nombres de GCS son globales y los del proyecto viejo (flighttracker-505314) siguen ocupados."
  type        = string
  default     = "506923"
}

variable "region" {
  description = "Region de GCP"
  type        = string
  default     = "us-east1"
}

variable "zone" {
  description = "Zona de GCP"
  type        = string
  default     = "us-east1-c"
}

variable "bucket_raw" {
  description = "Nombre del bucket RAW"
  type        = string
  default     = "flighttracker-raw-bts"
}

variable "bucket_curated" {
  description = "Nombre del bucket CURATED"
  type        = string
  default     = "flighttracker-curated-bts"
}

variable "pubsub_topic" {
  description = "Nombre del topic de Pub/Sub"
  type        = string
  default     = "bts-flights-rows"
}

variable "pubsub_subscription" {
  description = "Nombre de la suscripcion de Pub/Sub"
  type        = string
  default     = "bts-flights-sub"
}

variable "legacy_push_subscription_enabled" {
  description = "Suscripcion push heredada de Sprint 1. En el proyecto nuevo se arranca en false: el trigger Eventarc de la Gen2 ya crea su propia suscripcion y la duplicada era la causa del drift."
  type        = bool
  default     = false
}

variable "pubsub_dlq" {
  description = "Nombre del dead-letter topic"
  type        = string
  default     = "bts-flights-dlq"
}

variable "cloud_sql_instance" {
  description = "Nombre de la instancia Cloud SQL"
  type        = string
  default     = "flighttracker-db"
}

variable "cloud_sql_ssl_mode" {
  description = "SSL mode enforced for Cloud SQL public connectivity."
  type        = string
  default     = "ENCRYPTED_ONLY"
}

variable "cloud_sql_authorized_networks" {
  description = "Explicit allowlist for Cloud SQL public IP access. Leave empty to avoid broad public CIDRs."
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "cloud_sql_password_secret_id" {
  description = "Secret Manager secret id that stores the rotated Cloud SQL password."
  type        = string
  default     = "cloudsql-postgres-password"
}

variable "data_region" {
  description = "Region para datos (buckets y Cloud SQL)"
  type        = string
  default     = "us-central1"
}

variable "bucket_scripts" {
  description = "Bucket con los jobs de Spark y los CSV maestros de OpenFlights"
  type        = string
  default     = "flighttracker-scripts"
}

variable "bucket_functions" {
  description = "Bucket con los zips de las Cloud Functions. Lo crea bootstrap.sh antes del primer apply."
  type        = string
  default     = "flighttracker-function-sources"
}

variable "bigquery_dataset" {
  description = "Dataset de BigQuery para la capa Gold"
  type        = string
  default     = "flighttracker_gold"
}

variable "bigquery_location" {
  description = "Ubicacion del dataset de BigQuery"
  type        = string
  default     = "US"
}

variable "firestore_collection" {
  description = "Coleccion de Firestore usada por el serving batch"
  type        = string
  default     = "flights_v1"
}

variable "artifact_registry_repo" {
  description = "Repositorio de Artifact Registry con las imagenes de Cloud Run. Lo crea bootstrap.sh."
  type        = string
  default     = "flighttracker-functions"
}

variable "opensky_topic" {
  description = "Topic de Pub/Sub para estados de OpenSky"
  type        = string
  default     = "opensky-states-v1"
}

variable "opensky_dlq" {
  description = "Dead-letter topic de OpenSky"
  type        = string
  default     = "opensky-states-dlq"
}

variable "opensky_producer_enabled" {
  description = "Despliega el productor OpenSky en Cloud Run. Requiere que la imagen exista en Artifact Registry."
  type        = bool
  default     = true
}
