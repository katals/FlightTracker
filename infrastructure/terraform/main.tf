# ============================================
# 0. LOCALS Y DATA SOURCES
# ============================================
data "google_project" "project" {
  project_id = var.project_id
}

locals {
  # Los nombres de bucket son globales. Los del proyecto viejo siguen ocupados,
  # por eso todo lleva sufijo.
  bucket_raw       = "${var.bucket_raw}-${var.bucket_suffix}"
  bucket_curated   = "${var.bucket_curated}-${var.bucket_suffix}"
  bucket_scripts   = "${var.bucket_scripts}-${var.bucket_suffix}"
  bucket_functions = "${var.bucket_functions}-${var.bucket_suffix}"

  # La service account por defecto de Compute existe apenas se habilita la API.
  # Antes esto estaba clavado al numero del proyecto viejo (310107974919).
  function_sa = "${data.google_project.project.number}-compute@developer.gserviceaccount.com"

  eventarc_sa = "service-${data.google_project.project.number}@gcp-sa-eventarc.iam.gserviceaccount.com"

  artifact_registry_host = "${var.data_region}-docker.pkg.dev"
  api_image              = "${local.artifact_registry_host}/${var.project_id}/${var.artifact_registry_repo}/get-flights-api:latest"
  opensky_image          = "${local.artifact_registry_host}/${var.project_id}/${var.artifact_registry_repo}/opensky-producer:latest"
}

# ============================================
# 1. BUCKETS DE CLOUD STORAGE
# ============================================
resource "google_storage_bucket" "bucket_raw" {
  name                        = local.bucket_raw
  location                    = var.data_region
  force_destroy               = false
  uniform_bucket_level_access = true

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket" "bucket_curated" {
  name                        = local.bucket_curated
  location                    = var.data_region
  force_destroy               = false
  uniform_bucket_level_access = true

  depends_on = [google_project_service.required]
}

# Jobs de Spark y maestros OpenFlights. En Sprint 1 este bucket vivia fuera de
# Terraform (gs://flighttracker-scripts) y se perdio con el proyecto viejo.
resource "google_storage_bucket" "bucket_scripts" {
  name                        = local.bucket_scripts
  location                    = var.data_region
  force_destroy               = false
  uniform_bucket_level_access = true

  depends_on = [google_project_service.required]
}

# ============================================
# 2. PUB/SUB
# ============================================
resource "google_pubsub_topic" "topic" {
  name       = var.pubsub_topic
  depends_on = [google_project_service.required]
}

resource "google_pubsub_topic" "dlq" {
  name       = var.pubsub_dlq
  depends_on = [google_project_service.required]
}

resource "google_pubsub_topic" "opensky" {
  name       = var.opensky_topic
  depends_on = [google_project_service.required]
}

resource "google_pubsub_topic" "opensky_dlq" {
  name       = var.opensky_dlq
  depends_on = [google_project_service.required]
}

# Suscripcion push heredada. Queda desactivada por defecto: el event_trigger de
# validate_and_persist_bts ya crea su propia suscripcion via Eventarc y tener
# las dos era la causa del drift de Sprint 1.
resource "google_pubsub_subscription" "subscription" {
  count = var.legacy_push_subscription_enabled ? 1 : 0

  name  = var.pubsub_subscription
  topic = google_pubsub_topic.topic.name

  ack_deadline_seconds = 60

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }

  push_config {
    # data_region, no region: la funcion vive en us-central1.
    push_endpoint = "https://${var.data_region}-${var.project_id}.cloudfunctions.net/validate_and_persist_bts"
  }
}

# ============================================
# 3. FIRESTORE
# ============================================
# Nunca estuvo en Terraform. En el proyecto viejo se creo por consola, por eso
# no se recreaba de punta a punta.
resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = "nam5"
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.required]
}

# ============================================
# 4. BIGQUERY (CAPA GOLD)
# ============================================
resource "google_bigquery_dataset" "gold" {
  dataset_id  = var.bigquery_dataset
  location    = var.bigquery_location
  description = "Capa Gold - modelo en estrella FlightTracker"

  depends_on = [google_project_service.required]
}

# ============================================
# 5. CLOUD SQL (PostgreSQL)
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

  depends_on = [google_project_service.required]
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

  depends_on = [google_project_service.required]
}

# ============================================
# 6. CLOUD FUNCTIONS (2nd gen)
# ============================================
resource "google_cloudfunctions2_function" "validate_and_store" {
  name     = "validate_and_store_bts"
  location = var.data_region

  build_config {
    runtime     = "python311"
    entry_point = "validate_and_store_bts"
    source {
      storage_source {
        bucket = local.bucket_functions
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
      BUCKET_RAW     = local.bucket_raw
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_cloudfunctions2_function" "split_and_publish" {
  name        = "split_and_publish_bts"
  location    = var.data_region
  description = "Divide CSV en filas y publica en Pub/Sub"

  build_config {
    runtime     = "python311"
    entry_point = "split_and_publish_bts"
    source {
      storage_source {
        bucket = local.bucket_functions
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
    service_account_email = local.function_sa

    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.bucket_raw.name
    }
  }

  depends_on = [
    google_project_iam_member.eventarc_publisher,
    google_storage_bucket_iam_member.eventarc_viewer,
  ]
}

resource "google_cloudfunctions2_function" "validate_and_persist" {
  name        = "validate_and_persist_bts"
  location    = var.data_region
  description = "Valida y persiste vuelos en Firestore"

  build_config {
    runtime     = "python311"
    entry_point = "validate_and_persist_bts"
    source {
      storage_source {
        bucket = local.bucket_functions
        object = "validate_and_persist_bts.zip"
      }
    }
  }

  service_config {
    max_instance_count = 10
    available_memory   = "256M"
    timeout_seconds    = 60
    # Sin esto la funcion escribe en la coleccion "flights" y validate.sh
    # sondea "flights_v1": el check pasaba en Sprint 1 solo porque la variable
    # se habia puesto a mano en el redeploy.
    environment_variables = {
      GCP_PROJECT_ID       = var.project_id
      FIRESTORE_COLLECTION = var.firestore_collection
    }
  }

  event_trigger {
    trigger_region        = var.data_region
    event_type            = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic          = google_pubsub_topic.topic.id
    retry_policy          = "RETRY_POLICY_DO_NOT_RETRY"
    service_account_email = local.function_sa
  }

  depends_on = [google_firestore_database.default]
}

resource "google_cloudfunctions2_function" "project_opensky_state" {
  name        = "project_opensky_state"
  location    = var.data_region
  description = "Proyecta estados de OpenSky a Firestore live_flights"

  build_config {
    runtime     = "python311"
    entry_point = "project_opensky_state"
    source {
      storage_source {
        bucket = local.bucket_functions
        object = "proyectar_estado_opensky.zip"
      }
    }
  }

  service_config {
    max_instance_count = 10
    available_memory   = "256M"
    timeout_seconds    = 120
    environment_variables = {
      GCP_PROJECT_ID = var.project_id
    }
  }

  event_trigger {
    trigger_region        = var.data_region
    event_type            = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic          = google_pubsub_topic.opensky.id
    retry_policy          = "RETRY_POLICY_DO_NOT_RETRY"
    service_account_email = local.function_sa
  }

  depends_on = [google_firestore_database.default]
}

# ============================================
# 7. ORQUESTADOR BATCH
# ============================================
resource "google_cloudfunctions2_function" "start_batch_pipeline" {
  name        = "start_batch_pipeline"
  location    = var.region
  description = "Orquesta la ejecucion diaria del pipeline batch"

  build_config {
    runtime     = "python311"
    entry_point = "start_batch_pipeline"
    source {
      storage_source {
        # Antes: gcf-v2-sources-310107974919-us-east1 (bucket autogenerado del
        # proyecto viejo). Ahora el zip lo sube deploy.sh como los demas.
        bucket = local.bucket_functions
        object = "start_batch_pipeline.zip"
      }
    }
  }

  service_config {
    max_instance_count = 100
    available_memory   = "256M"
    timeout_seconds    = 300
    environment_variables = {
      GCP_PROJECT_ID = var.project_id
      GCP_REGION     = var.region
      BUCKET_SCRIPTS = local.bucket_scripts
      BUCKET_RAW     = local.bucket_raw
      BUCKET_CURATED = local.bucket_curated
    }
  }

  depends_on = [google_project_service.required]
}

# ============================================
# 8. CLOUD SCHEDULER
# ============================================
resource "google_cloud_scheduler_job" "daily_pipeline" {
  name        = "daily-bts-pipeline"
  description = "Ejecuta el pipeline batch diariamente a las 8 AM"
  region      = var.region

  schedule  = "0 8 * * *"
  time_zone = "America/Bogota"

  http_target {
    uri         = google_cloudfunctions2_function.start_batch_pipeline.service_config[0].uri
    http_method = "GET"
  }

  retry_config {
    retry_count = 5
  }
}

resource "google_cloud_scheduler_job" "opensky_poll" {
  count = var.opensky_producer_enabled ? 1 : 0

  name        = "opensky-poll"
  description = "Dispara el productor OpenSky cada 5 minutos"
  region      = var.region

  schedule  = "*/5 * * * *"
  time_zone = "America/Bogota"

  http_target {
    uri         = google_cloud_run_service.opensky_producer[0].status[0].url
    http_method = "GET"
  }

  retry_config {
    retry_count = 3
  }
}

# ============================================
# 9. CLOUD RUN
# ============================================
resource "google_cloud_run_service" "get_flights_api" {
  name     = "get-flights-api"
  location = var.data_region

  template {
    spec {
      containers {
        image = local.api_image
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "FIRESTORE_COLLECTION"
          value = var.firestore_collection
        }
        env {
          name  = "BIGQUERY_DATASET"
          value = var.bigquery_dataset
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

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_service" "opensky_producer" {
  count = var.opensky_producer_enabled ? 1 : 0

  name     = "opensky-producer"
  location = var.data_region

  template {
    spec {
      containers {
        image = local.opensky_image
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "PUBSUB_TOPIC"
          value = var.opensky_topic
        }
        env {
          name  = "REQUEST_TIMEOUT_SEC"
          value = "30"
        }
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_service_iam_member" "public_invoke" {
  service  = google_cloud_run_service.get_flights_api.name
  location = google_cloud_run_service.get_flights_api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "opensky_invoke" {
  count = var.opensky_producer_enabled ? 1 : 0

  service  = google_cloud_run_service.opensky_producer[0].name
  location = google_cloud_run_service.opensky_producer[0].location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ============================================
# 10. IAM
# ============================================
resource "google_storage_bucket_iam_member" "eventarc_viewer" {
  bucket = google_storage_bucket.bucket_raw.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${local.eventarc_sa}"
}

resource "google_project_iam_member" "eventarc_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${local.eventarc_sa}"
}

resource "google_project_iam_member" "gcs_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gs-project-accounts.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "orchestrator_dataproc" {
  project = var.project_id
  role    = "roles/dataproc.admin"
  member  = "serviceAccount:${local.function_sa}"
}

resource "google_project_iam_member" "orchestrator_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${local.function_sa}"
}

resource "google_project_iam_member" "function_datastore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${local.function_sa}"
}

resource "google_project_iam_member" "function_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${local.function_sa}"
}

resource "google_project_iam_member" "function_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${local.function_sa}"
}
