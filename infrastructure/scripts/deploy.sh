#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TERRAFORM_DIR="${REPO_ROOT}/infrastructure/terraform"
FUNCTIONS_DIR="${REPO_ROOT}/backend/functions"
API_DIR="${REPO_ROOT}/backend/api/get_flights"
DB_SEED_SCRIPT="${REPO_ROOT}/database/scripts/seed_openflights.py"
ARTIFACTS_DIR="${REPO_ROOT}/.artifacts"
FUNCTION_ARTIFACTS_DIR="${ARTIFACTS_DIR}/functions"

DEFAULT_ENV="dev"
DEFAULT_DATA_REGION="us-central1"
DEFAULT_BATCH_REGION="us-east1"
DEFAULT_FUNCTION_ARTIFACT_BUCKET="flighttracker-function-sources"

usage() {
  cat <<'EOF'
Usage:
  ./infrastructure/scripts/deploy.sh [options]

Options:
  --env <dev|test|prod>           Logical environment. Default: dev
  --project-id <id>               GCP project id. Required.
  --data-region <region>          Data region. Default: us-central1
  --batch-region <region>         Batch/orchestration region. Default: us-east1
  --function-artifact-bucket <b>  Bucket for Terraform function zips.
  --skip-api-build                Do not build/push the Cloud Run API image.
  --skip-artifact-upload          Do not upload function zip artifacts to GCS.
  --run-seed                      Run OpenFlights seed after apply. Requires DB_* env vars.
  --run-smoke                     Run validate.sh after apply.
  --apply                         Run terraform apply after plan if safe.
  -h, --help                      Show this help message.

Current Sprint 1 behavior:
  - always packages Terraform-managed Cloud Function sources
  - can build the API image with Cloud Build
  - runs terraform init/validate/plan
  - blocks terraform apply if known Terraform drift is still present
EOF
}

log() {
  printf '[deploy] %s\n' "$*"
}

fail() {
  printf '[deploy] ERROR: %s\n' "$*" >&2
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
    fail "Terraform CLI is not usable in this shell. Install it first and rerun deploy.sh."
  fi

  log "Terraform available: $(head -n 1 <<<"${output}")"
}

require_active_gcloud_account() {
  local active_account
  active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -n 1)"
  [[ -n "${active_account}" ]] || fail "No active gcloud account found. Run 'gcloud auth login' first."
  log "Active gcloud account: ${active_account}"
}

ensure_bucket_exists() {
  local bucket_uri="gs://${FUNCTION_ARTIFACT_BUCKET}"
  gcloud storage buckets describe "${bucket_uri}" --project="${PROJECT_ID}" >/dev/null 2>&1 \
    || fail "Function artifact bucket does not exist: ${bucket_uri}"
}

package_function_zip() {
  local function_name="$1"
  local source_dir="${FUNCTIONS_DIR}/${function_name}"
  local output_zip="${FUNCTION_ARTIFACTS_DIR}/${function_name}.zip"

  [[ -d "${source_dir}" ]] || fail "Missing function directory: ${source_dir}"

  rm -f "${output_zip}"
  (
    cd "${source_dir}"
    zip -qr "${output_zip}" . \
      -x '__pycache__/*' \
      -x '*.pyc' \
      -x '.pytest_cache/*'
  )
  log "Packaged ${function_name} -> ${output_zip}"
}

upload_function_zip() {
  local function_name="$1"
  local output_zip="${FUNCTION_ARTIFACTS_DIR}/${function_name}.zip"
  local target_uri="gs://${FUNCTION_ARTIFACT_BUCKET}/${function_name}.zip"
  gcloud storage cp "${output_zip}" "${target_uri}" --project="${PROJECT_ID}" >/dev/null
  log "Uploaded ${function_name} artifact -> ${target_uri}"
}

build_api_image() {
  local image_uri="us-central1-docker.pkg.dev/${PROJECT_ID}/flighttracker-functions/get-flights-api:latest"
  log "Building Cloud Run API image with Cloud Build"
  gcloud builds submit "${API_DIR}" \
    --project="${PROJECT_ID}" \
    --tag "${image_uri}" \
    --quiet
  log "API image ready: ${image_uri}"
}

terraform_init_validate_plan() {
  local plan_file="${ARTIFACTS_DIR}/tfplan.${ENV_NAME}"
  mkdir -p "${ARTIFACTS_DIR}"
  (
    cd "${TERRAFORM_DIR}"
    terraform init -input=false
    terraform validate
    terraform plan \
      -input=false \
      -out="${plan_file}" \
      -var="project_id=${PROJECT_ID}" \
      -var="region=${BATCH_REGION}" \
      -var="data_region=${DATA_REGION}"
  )
  [[ -s "${plan_file}" ]] || fail "Terraform plan did not produce a usable plan file: ${plan_file}"
  log "Terraform plan created: ${plan_file}"
}

detect_known_terraform_drift() {
  local main_tf="${TERRAFORM_DIR}/main.tf"

  if grep -q 'trigger_region[[:space:]]*=[[:space:]]*var.region' "${main_tf}"; then
    return 0
  fi

  if grep -q 'push_endpoint = "https://${var.region}-${var.project_id}.cloudfunctions.net/validate_and_persist_bts"' "${main_tf}"; then
    return 0
  fi

  return 1
}

run_seed_if_requested() {
  [[ "${RUN_SEED}" == "true" ]] || return 0

  [[ -n "${DB_HOST:-}" ]] || fail "DB_HOST is required when --run-seed is used."
  [[ -n "${DB_NAME:-}" ]] || fail "DB_NAME is required when --run-seed is used."
  [[ -n "${DB_USER:-}" ]] || fail "DB_USER is required when --run-seed is used."
  [[ -n "${DB_PASS:-}" ]] || fail "DB_PASS is required when --run-seed is used."

  require_command python3
  log "Running OpenFlights seed"
  python3 "${DB_SEED_SCRIPT}"
}

run_smoke_if_requested() {
  [[ "${RUN_SMOKE}" == "true" ]] || return 0
  local validate_script="${SCRIPT_DIR}/validate.sh"
  [[ -f "${validate_script}" ]] || fail "validate.sh not found: ${validate_script}"
  log "Running validate.sh smoke workflow"
  bash "${validate_script}" --project-id "${PROJECT_ID}" --env "${ENV_NAME}"
}

ENV_NAME="${DEFAULT_ENV}"
PROJECT_ID="${PROJECT_ID:-}"
DATA_REGION="${DATA_REGION:-${DEFAULT_DATA_REGION}}"
BATCH_REGION="${BATCH_REGION:-${DEFAULT_BATCH_REGION}}"
FUNCTION_ARTIFACT_BUCKET="${FUNCTION_ARTIFACT_BUCKET:-${DEFAULT_FUNCTION_ARTIFACT_BUCKET}}"
SKIP_API_BUILD="false"
SKIP_ARTIFACT_UPLOAD="false"
RUN_SEED="false"
RUN_SMOKE="false"
RUN_APPLY="false"

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
    --function-artifact-bucket)
      FUNCTION_ARTIFACT_BUCKET="${2:-}"
      shift 2
      ;;
    --skip-api-build)
      SKIP_API_BUILD="true"
      shift
      ;;
    --skip-artifact-upload)
      SKIP_ARTIFACT_UPLOAD="true"
      shift
      ;;
    --run-seed)
      RUN_SEED="true"
      shift
      ;;
    --run-smoke)
      RUN_SMOKE="true"
      shift
      ;;
    --apply)
      RUN_APPLY="true"
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

[[ -n "${PROJECT_ID}" ]] || fail "PROJECT_ID is required. Pass --project-id."

require_command gcloud
require_command terraform
require_command zip
require_terraform_usable

require_active_gcloud_account
gcloud config set project "${PROJECT_ID}" >/dev/null

mkdir -p "${FUNCTION_ARTIFACTS_DIR}"

log "Packaging Terraform-managed Cloud Function sources"
package_function_zip "validate_and_store_bts"
package_function_zip "split_and_publish_bts"
package_function_zip "validate_and_persist_bts"

log "Skipping start_batch_pipeline zip because Terraform still points to an autogenerated GCF source bucket"
log "Skipping project_opensky_state zip because it is outside the Terraform scope used in Sprint 1"

if [[ "${SKIP_ARTIFACT_UPLOAD}" == "false" ]]; then
  ensure_bucket_exists
  upload_function_zip "validate_and_store_bts"
  upload_function_zip "split_and_publish_bts"
  upload_function_zip "validate_and_persist_bts"
else
  log "Skipping artifact upload by request"
fi

if [[ "${SKIP_API_BUILD}" == "false" ]]; then
  build_api_image
else
  log "Skipping API image build by request"
fi

terraform_init_validate_plan

if [[ "${RUN_APPLY}" == "true" ]]; then
  if detect_known_terraform_drift; then
    fail "Refusing terraform apply: known Sprint 1 drift is still present in terraform/main.tf. Fix validate_and_persist_bts region/legacy drift first."
  fi

  (
    cd "${TERRAFORM_DIR}"
    terraform apply -input=false "${ARTIFACTS_DIR}/tfplan.${ENV_NAME}"
  )
  log "Terraform apply completed"
  run_seed_if_requested
  run_smoke_if_requested
else
  log "Plan-only execution completed. terraform apply was not requested."
fi

cat <<EOF

[deploy] Deploy workflow finished.

Artifacts:
  - Function zips: ${FUNCTION_ARTIFACTS_DIR}
  - Terraform plan: ${ARTIFACTS_DIR}/tfplan.${ENV_NAME}

Notes:
  - This script intentionally blocks apply while known Terraform drift remains.
  - Use validate.sh for post-deploy checks once that script is completed.
EOF
