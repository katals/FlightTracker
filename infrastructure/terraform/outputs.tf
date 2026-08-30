output "api_url" {
  description = "URL publica de la API de serving"
  value       = google_cloud_run_service.get_flights_api.status[0].url
}

output "opensky_producer_url" {
  description = "URL del productor OpenSky"
  value       = var.opensky_producer_enabled ? google_cloud_run_service.opensky_producer[0].status[0].url : null
}

output "start_batch_pipeline_url" {
  description = "URL del orquestador batch"
  value       = google_cloudfunctions2_function.start_batch_pipeline.service_config[0].uri
}

output "buckets" {
  description = "Buckets creados por Terraform"
  value = {
    raw     = google_storage_bucket.bucket_raw.name
    curated = google_storage_bucket.bucket_curated.name
    scripts = google_storage_bucket.bucket_scripts.name
  }
}
