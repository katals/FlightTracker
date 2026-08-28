variable "project_id" {
  description = "ID del proyecto GCP"
  type        = string
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
  description = "Keep the legacy push subscription during the idempotency rollout; disable only after Eventarc is verified as the sole consumer."
  type        = bool
  default     = true
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
