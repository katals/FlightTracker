terraform {
  backend "gcs" {
    bucket = "flighttracker-tfstate-506923"
    prefix = "terraform/state"
  }
}
