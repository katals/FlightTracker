# ============================================
# 0. HABILITACION DE APIs
# ============================================
# El proyecto nuevo (flighttracker-506923) arranca vacio. bootstrap.sh ya
# habilita las APIs por gcloud; estos recursos las dejan declaradas en codigo
# para que la reproducibilidad no dependa del script.
locals {
  required_services = [
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",
    "dataproc.googleapis.com",
    "eventarc.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
  ]
}

resource "google_project_service" "required" {
  for_each = toset(local.required_services)

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}
