#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TERRAFORM_DIR="${REPO_ROOT}/infrastructure/terraform"
ARTIFACTS_DIR="${REPO_ROOT}/.artifacts"
BACKEND_FILE="${TERRAFORM_DIR}/backend.tf"

DEFAULT_ENV="dev"
DEFAULT_DATA_REGION="us-central1"
DEFAULT_BATCH_REGION="us-east1"

usage() {
  cat <<'EOF'
Usage:
  ./infrastructure/scripts/destroy.sh [options]

Options:
  --env <dev|test|prod>          Logical environment label. Default: dev
  --project-id <id>              GCP project id. Required.
  --data-region <region>         Data region. Default: us-central1
  --batch-region <region>        Batch/orchestration region. Default: us-east1
  --auto-approve                 Skip the terraform interactive approval prompt.
  --allow-prod                   Required to target env=prod.
  --delete-state-backend         Also delete the Terraform backend bucket after destroy.
  --confirm <phrase>             Explicit confirmation phrase. Required:
                                 "destroy-<env>-<project-id>"
  -h, --help                     Show this help message.

Safety defaults:
  - refuses env=prod unless --allow-prod is set
  - preserves the Terraform backend bucket unless --delete-state-backend is used
  - only removes local controlled artifacts under .artifacts/
EOF
}

log() {
  printf '[destroy] %s\n' "$*"
}

fail() {
  printf '[destroy] ERROR: %s\n' "$*" >&2
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
    fail "Terraform CLI is not usable in this shell."
  fi

  log "Terraform available: $(head -n 1 <<<"${output}")"
}

require_active_gcloud_account() {
  local active_account
  active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -n 1)"
  [[ -n "${active_account}" ]] || fail "No active gcloud account found."
  log "Active gcloud account: ${active_account}"
}

read_backend_bucket() {
  if [[ -f "${BACKEND_FILE}" ]]; then
    awk -F'"' '/bucket[[:space:]]*=/ {print $2; exit}' "${BACKEND_FILE}"
  fi
}

cleanup_local_artifacts() {
  if [[ -d "${ARTIFACTS_DIR}" ]]; then
    rm -rf "${ARTIFACTS_DIR}"
    log "Removed local controlled artifacts: ${ARTIFACTS_DIR}"
  else
    log "No local artifacts to remove"
  fi
}

destroy_backend_bucket_if_requested() {
  [[ "${DELETE_STATE_BACKEND}" == "true" ]] || return 0

  local backend_bucket
  backend_bucket="$(read_backend_bucket)"
  [[ -n "${backend_bucket}" ]] || fail "Could not determine backend bucket from backend.tf"

  log "Deleting Terraform backend bucket contents: gs://${backend_bucket}"
  gcloud storage rm --recursive "gs://${backend_bucket}/**" >/dev/null 2>&1 || true
  log "Deleting Terraform backend bucket: gs://${backend_bucket}"
  gcloud storage buckets delete "gs://${backend_bucket}" --quiet
}

ENV_NAME="${DEFAULT_ENV}"
PROJECT_ID="${PROJECT_ID:-}"
DATA_REGION="${DATA_REGION:-${DEFAULT_DATA_REGION}}"
BATCH_REGION="${BATCH_REGION:-${DEFAULT_BATCH_REGION}}"
AUTO_APPROVE="false"
ALLOW_PROD="false"
DELETE_STATE_BACKEND="false"
CONFIRM_PHRASE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENV_NAME="${2:-}"
      shift 2
      ;;
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
    --auto-approve)
      AUTO_APPROVE="true"
      shift
      ;;
    --allow-prod)
      ALLOW_PROD="true"
      shift
      ;;
    --delete-state-backend)
      DELETE_STATE_BACKEND="true"
      shift
      ;;
    --confirm)
      CONFIRM_PHRASE="${2:-}"
      shift 2
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

[[ -n "${PROJECT_ID}" ]] || fail "PROJECT_ID is required. Pass --project-id."

if [[ "${ENV_NAME}" == "prod" && "${ALLOW_PROD}" != "true" ]]; then
  fail "Refusing to target prod without --allow-prod."
fi

EXPECTED_CONFIRM="destroy-${ENV_NAME}-${PROJECT_ID}"
if [[ "${CONFIRM_PHRASE}" != "${EXPECTED_CONFIRM}" ]]; then
  fail "Confirmation phrase mismatch. Re-run with: --confirm ${EXPECTED_CONFIRM}"
fi

require_command gcloud
require_command terraform
require_terraform_usable
require_active_gcloud_account

gcloud config set project "${PROJECT_ID}" >/dev/null

log "Environment label: ${ENV_NAME}"
log "Project id       : ${PROJECT_ID}"
log "Data region      : ${DATA_REGION}"
log "Batch region     : ${BATCH_REGION}"

(
  cd "${TERRAFORM_DIR}"
  terraform init -input=false >/dev/null
  if [[ "${AUTO_APPROVE}" == "true" ]]; then
    terraform destroy \
      -input=false \
      -auto-approve \
      -var="project_id=${PROJECT_ID}" \
      -var="region=${BATCH_REGION}" \
      -var="data_region=${DATA_REGION}"
  else
    terraform destroy \
      -var="project_id=${PROJECT_ID}" \
      -var="region=${BATCH_REGION}" \
      -var="data_region=${DATA_REGION}"
  fi
)

cleanup_local_artifacts
destroy_backend_bucket_if_requested

cat <<EOF

[destroy] Destroy workflow completed.

Notes:
  - Terraform backend bucket was preserved by default.
  - Only local controlled artifacts under .artifacts/ were removed.
EOF
