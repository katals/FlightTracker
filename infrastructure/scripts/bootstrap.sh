#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TERRAFORM_DIR="${REPO_ROOT}/infrastructure/terraform"
BACKEND_FILE="${TERRAFORM_DIR}/backend.tf"

DEFAULT_DATA_REGION="us-central1"
DEFAULT_BATCH_REGION="us-east1"
DEFAULT_STATE_PREFIX="terraform/state"

usage() {
  cat <<'EOF'
Usage:
  ./infrastructure/scripts/bootstrap.sh [options]

Options:
  --project-id <id>         GCP project id. Falls back to $PROJECT_ID or gcloud config.
  --data-region <region>    Data region for shared services. Default: us-central1
  --batch-region <region>   Batch/orchestration region. Default: us-east1
  --state-bucket <name>     Terraform backend bucket name. Defaults to backend.tf bucket.
  --state-region <region>   Region for the Terraform state bucket. Default: data region
  --state-prefix <prefix>   Terraform state prefix. Default: terraform/state
  --skip-docker-check       Do not fail if docker is unavailable.
  -h, --help                Show this help message.

This script is a bootstrap helper only. It can:
  - validate local prerequisites
  - validate active gcloud authentication
  - set the active GCP project
  - enable foundational APIs
  - create the Terraform backend bucket if it does not exist

It intentionally does NOT:
  - run terraform apply
  - deploy application artifacts
  - create business resources outside Terraform
EOF
}

log() {
  printf '[bootstrap] %s\n' "$*"
}

fail() {
  printf '[bootstrap] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  local cmd="$1"
  command -v "${cmd}" >/dev/null 2>&1 || fail "Required command not found: ${cmd}"
}

require_terraform_usable() {
  local output
  local status

  set +e
  output="$(terraform version 2>&1)"
  status=$?
  set -e

  if [[ ${status} -ne 0 ]] || grep -q "Follow the instructions at https://developer.hashicorp.com/terraform/install" <<<"${output}"; then
    fail "Terraform CLI is not usable in this shell. Install it first and rerun bootstrap.sh."
  fi

  log "Terraform available: $(head -n 1 <<<"${output}")"
}

read_backend_bucket() {
  if [[ -f "${BACKEND_FILE}" ]]; then
    awk -F'"' '/bucket[[:space:]]*=/ {print $2; exit}' "${BACKEND_FILE}"
  fi
}

read_backend_prefix() {
  if [[ -f "${BACKEND_FILE}" ]]; then
    awk -F'"' '/prefix[[:space:]]*=/ {print $2; exit}' "${BACKEND_FILE}"
  fi
}

require_active_gcloud_account() {
  local active_account
  active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -n 1)"
  [[ -n "${active_account}" ]] || fail "No active gcloud account found. Run 'gcloud auth login' first."
  log "Active gcloud account: ${active_account}"
}

detect_project_id() {
  if [[ -n "${PROJECT_ID:-}" ]]; then
    printf '%s' "${PROJECT_ID}"
    return
  fi

  local configured_project
  configured_project="$(gcloud config get-value project 2>/dev/null || true)"
  if [[ -n "${configured_project}" && "${configured_project}" != "(unset)" ]]; then
    printf '%s' "${configured_project}"
    return
  fi

  fail "PROJECT_ID is required. Pass --project-id or export PROJECT_ID."
}

validate_project_access() {
  gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)' >/dev/null 2>&1 \
    || fail "Could not access project '${PROJECT_ID}'. Check permissions and project id."
}

ensure_backend_bucket() {
  local bucket_uri="gs://${STATE_BUCKET}"

  if gcloud storage buckets describe "${bucket_uri}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    log "Terraform backend bucket already exists: ${bucket_uri}"
    return
  fi

  log "Creating Terraform backend bucket: ${bucket_uri}"
  gcloud storage buckets create "${bucket_uri}" \
    --project="${PROJECT_ID}" \
    --location="${STATE_REGION}" \
    --uniform-bucket-level-access
}

enable_required_apis() {
  local services=(
    artifactregistry.googleapis.com
    cloudbuild.googleapis.com
    cloudfunctions.googleapis.com
    cloudscheduler.googleapis.com
    compute.googleapis.com
    dataproc.googleapis.com
    eventarc.googleapis.com
    firestore.googleapis.com
    iam.googleapis.com
    logging.googleapis.com
    monitoring.googleapis.com
    pubsub.googleapis.com
    run.googleapis.com
    secretmanager.googleapis.com
    sqladmin.googleapis.com
    storage.googleapis.com
  )

  log "Enabling required foundational APIs"
  gcloud services enable "${services[@]}" --project="${PROJECT_ID}"
}

SKIP_DOCKER_CHECK="false"
PROJECT_ID="${PROJECT_ID:-}"
DATA_REGION="${DATA_REGION:-${DEFAULT_DATA_REGION}}"
BATCH_REGION="${BATCH_REGION:-${DEFAULT_BATCH_REGION}}"
STATE_BUCKET="${STATE_BUCKET:-}"
STATE_REGION="${STATE_REGION:-}"
STATE_PREFIX="${STATE_PREFIX:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id)
      PROJECT_ID="${2:-}"
      shift 2
      ;;
    --data-region)
      DATA_REGION="${2:-}"
      shift 2
      ;;
    --batch-region)
      BATCH_REGION="${2:-}"
      shift 2
      ;;
    --state-bucket)
      STATE_BUCKET="${2:-}"
      shift 2
      ;;
    --state-region)
      STATE_REGION="${2:-}"
      shift 2
      ;;
    --state-prefix)
      STATE_PREFIX="${2:-}"
      shift 2
      ;;
    --skip-docker-check)
      SKIP_DOCKER_CHECK="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

require_command gcloud
require_command terraform
require_terraform_usable

if [[ "${SKIP_DOCKER_CHECK}" == "false" ]]; then
  require_command docker
else
  log "Skipping docker check by request"
fi

require_active_gcloud_account
PROJECT_ID="$(detect_project_id)"
validate_project_access

if [[ -z "${STATE_BUCKET}" ]]; then
  STATE_BUCKET="$(read_backend_bucket)"
fi
[[ -n "${STATE_BUCKET}" ]] || fail "Could not determine Terraform backend bucket. Pass --state-bucket."

if [[ -z "${STATE_PREFIX}" ]]; then
  STATE_PREFIX="$(read_backend_prefix)"
fi
STATE_PREFIX="${STATE_PREFIX:-${DEFAULT_STATE_PREFIX}}"
STATE_REGION="${STATE_REGION:-${DATA_REGION}}"

log "Project id      : ${PROJECT_ID}"
log "Data region     : ${DATA_REGION}"
log "Batch region    : ${BATCH_REGION}"
log "State bucket    : ${STATE_BUCKET}"
log "State region    : ${STATE_REGION}"
log "State prefix    : ${STATE_PREFIX}"
log "Terraform dir   : ${TERRAFORM_DIR}"

log "Setting active gcloud project"
gcloud config set project "${PROJECT_ID}" >/dev/null

enable_required_apis
ensure_backend_bucket

cat <<EOF

[bootstrap] Bootstrap completed successfully.

Next suggested commands:
  cd "${TERRAFORM_DIR}"
  terraform init
  terraform validate
  terraform plan -var="project_id=${PROJECT_ID}"

Reminder:
  - This script only prepares foundational prerequisites.
  - Resource creation for the solution must continue through Terraform, not manual gcloud commands.
EOF
