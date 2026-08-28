# State migration declarations for the first safe Terraform apply.
#
# The existing push subscription is currently tracked at an unindexed address.
# Adding count for a staged retirement would otherwise make Terraform propose a
# destructive replacement. This move changes only the state address.
moved {
  from = google_pubsub_subscription.subscription
  to   = google_pubsub_subscription.subscription[0]
}

# Do not remove the legacy Cloud Run API in this change. The service in
# us-central1 will be imported into a canonical resource only after its
# configuration is reviewed with an authenticated `terraform plan`. That
# preserves a tested rollback path while the repository port is introduced.
