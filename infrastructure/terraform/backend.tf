terraform {
  backend "gcs" {
    bucket = "flighttracker-terraform-state-flighttracker-505314"
    prefix = "terraform/state"
  }
}
