# ============================================
# 1. BUCKETS DE CLOUD STORAGE
# ============================================
resource "google_storage_bucket" "bucket_raw" {
  name                        = var.bucket_raw
  location                    = var.data_region
  force_destroy               = false
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "bucket_curated" {
  name                        = var.bucket_curated
  location                    = var.data_region
  force_destroy               = false
  uniform_bucket_level_access = true
}

# ============================================
# 2. PUB/SUB
# ============================================
resource "google_pubsub_topic" "topic" {
  name = var.pubsub_topic
}

resource "google_pubsub_topic" "dlq" {
  name = var.pubsub_dlq
}

resource "google_pubsub_subscription" "subscription" {
  # This is the legacy push consumer. The Gen2 function event trigger already
  # creates its own Eventarc subscription. Keep this resource during the
  # idempotency rollout, then set legacy_push_subscription_enabled=false in a
  # separate, verified apply to retire the duplicate consumer.
  count = var.legacy_push_subscription_enabled ? 1 : 0

  name  = var.pubsub_subscription
  topic = google_pubsub_topic.topic.name

  ack_deadline_seconds = 60

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }

  push_config {
    push_endpoint = "https://${var.region}-${var.project_id}.cloudfunctions.net/validate_and_persist_bts"
  }
}

# ============================================
# 3. CLOUD SQL (PostgreSQL)
# ============================================
resource "google_sql_database_instance" "postgres" {
  name             = var.cloud_sql_instance
  database_version = "POSTGRES_14"
  region           = var.data_region

  settings {
    tier              = "db-f1-micro"
    activation_policy = "ALWAYS"
    disk_autoresize   = false
    disk_size         = 10

    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = var.cloud_sql_ssl_mode

      dynamic "authorized_networks" {
        for_each = var.cloud_sql_authorized_networks
        content {
          name  = authorized_networks.value.name
          value = authorized_networks.value.value
        }
      }
    }
  }

  deletion_protection = false
}

resource "google_sql_database" "postgres_db" {
  name     = "flighttracker"
  instance = google_sql_database_instance.postgres.name
}

resource "google_secret_manager_secret" "cloud_sql_password" {
  secret_id = var.cloud_sql_password_secret_id

  replication {
    auto {}
  }
}

# ============================================
# 4. CLOUD FUNCTIONS (2nd gen) - COMPLETAS
# ============================================

# Funcion 1: validate_and_store_bts (HTTP trigger)
resource "google_cloudfunctions2_function" "validate_and_store" {
  name     = "validate_and_store_bts"
  location = var.data_region

  build_config {
    runtime     = "python311"
    entry_point = "validate_and_store_bts"
    source {
      storage_source {
        bucket = "flighttracker-function-sources"
        object = "validate_and_store_bts.zip"
      }
    }
  }

  service_config {
    max_instance_count = 100
    available_memory   = "256M"
    timeout_seconds    = 60
    environment_variables = {
      GCP_PROJECT_ID = var.project_id
      BUCKET_RAW     = var.bucket_raw
    }
  }
}

# Funcion 2: split_and_publish_bts (activada por Eventarc)
resource "google_cloudfunctions2_function" "split_and_publish" {
  name        = "split_and_publish_bts"
  location    = var.data_region
  description = "Divide CSV en filas y publica en Pub/Sub"

  build_config {
    runtime     = "python311"
    entry_point = "split_and_publish_bts"
    source {
      storage_source {
        bucket = "flighttracker-function-sources"
        object = "split_and_publish_bts.zip"
      }
    }
  }

  service_config {
    max_instance_count = 10
    available_memory   = "512M"
    timeout_seconds    = 540
    environment_variables = {
      GCP_PROJECT_ID = var.project_id
      PUBSUB_TOPIC   = var.pubsub_topic
    }
  }

  event_trigger {
    trigger_region        = var.data_region
    event_type            = "google.cloud.storage.object.v1.finalized"
    retry_policy          = "RETRY_POLICY_DO_NOT_RETRY"
    service_account_email = data.google_service_account.function_sa.email

    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.bucket_raw.name
    }
  }
}

# Funcion 3: validate_and_persist_bts (Pub/Sub trigger)
resource "google_cloudfunctions2_function" "validate_and_persist" {
  name        = "validate_and_persist_bts"
  location    = var.data_region
  description = "Valida y persiste vuelos en Firestore"

  build_config {
    runtime     = "python311"
    entry_point = "validate_and_persist_bts"
    source {
      storage_source {
        bucket = "flighttracker-function-sources"
        object = "validate_and_persist_bts.zip"
      }
    }
  }

  service_config {
    max_instance_count = 10
    available_memory   = "256M"
    timeout_seconds    = 60
  }

  event_trigger {
    trigger_region        = var.data_region
    event_type            = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic          = google_pubsub_topic.topic.id
    retry_policy          = "RETRY_POLICY_DO_NOT_RETRY"
    service_account_email = data.google_service_account.function_sa.email
  }
}

# ============================================
# 5. ORQUESTADOR (start_batch_pipeline)
# ============================================
resource "google_cloudfunctions2_function" "start_batch_pipeline" {
  name        = "start_batch_pipeline"
  location    = "us-east1"
  description = "Orquesta la ejecución diaria del pipeline batch"

  build_config {
    runtime     = "python311"
    entry_point = "start_batch_pipeline"
    source {
      storage_source {
        bucket = "gcf-v2-sources-310107974919-us-east1"
        object = "start_batch_pipeline/function-source.zip"
      }
    }
  }

  service_config {
    max_instance_count = 100
    available_memory   = "256M"
    timeout_seconds    = 300
    environment_variables = {
      GCP_PROJECT_ID = var.project_id
      GCP_REGION     = "us-east1"
    }
  }
}

# ============================================
# 6. CLOUD SCHEDULER
# ============================================
resource "google_cloud_scheduler_job" "daily_pipeline" {
  name        = "daily-bts-pipeline"
  description = "Ejecuta el pipeline batch diariamente a las 8 AM"
  region      = var.region

  schedule  = "0 8 * * *"
  time_zone = "America/Bogota"

  http_target {
    uri         = "https://us-east1-flighttracker-505314.cloudfunctions.net/start_batch_pipeline"
    http_method = "GET"
  }

  retry_config {
    retry_count = 5
  }
}

# ============================================
# 7. API REST (FlightTracker API)
# ============================================
resource "google_cloud_run_service" "get_flights_api" {
  name     = "get-flights-api"
  location = var.region

  template {
    spec {
      containers {
        image = "us-central1-docker.pkg.dev/${var.project_id}/flighttracker-functions/get-flights-api:latest"
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        resources {
          limits = {
            cpu    = "1"
            memory = "256Mi"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Permiso para que cualquier usuario pueda invocar la API
resource "google_cloud_run_service_iam_member" "public_invoke" {
  service  = google_cloud_run_service.get_flights_api.name
  location = google_cloud_run_service.get_flights_api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ============================================
# 8. DATA SOURCES
# ============================================
data "google_service_account" "function_sa" {
  account_id = "310107974919-compute@developer.gserviceaccount.com"
}

data "google_project" "project" {
  project_id = var.project_id
}

# ============================================
# 9. IAM (PERMISOS)
# ============================================
resource "google_storage_bucket_iam_member" "eventarc_viewer" {
  bucket = var.bucket_raw
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-eventarc.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "eventarc_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-eventarc.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "orchestrator_dataproc" {
  project = var.project_id
  role    = "roles/dataproc.admin"
  member  = "serviceAccount:${data.google_service_account.function_sa.email}"
}

resource "google_project_iam_member" "orchestrator_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${data.google_service_account.function_sa.email}"
}
