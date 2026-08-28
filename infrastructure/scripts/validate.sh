#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TERRAFORM_DIR="${REPO_ROOT}/infrastructure/terraform"
DQ_DIR="${REPO_ROOT}/docs/sprint1/data-assessment"

DEFAULT_ENV="dev"
DEFAULT_DATA_REGION="us-central1"
DEFAULT_BATCH_REGION="us-east1"
DEFAULT_API_REGION="us-central1"
DEFAULT_BIGQUERY_DATASET="flighttracker_gold"
DEFAULT_BIGQUERY_TABLE="fact_flights"
DEFAULT_API_SERVICE="get-flights-api"
DEFAULT_SCHEDULER_JOB="daily-bts-pipeline"
DEFAULT_PUBSUB_TOPIC="bts-flights-rows"
DEFAULT_FIRESTORE_COLLECTION="flights_v1"

usage() {
  cat <<'EOF'
Usage:
  ./infrastructure/scripts/validate.sh [options]

Options:
  --project-id <id>              GCP project id. Required.
  --env <dev|test|prod>          Logical environment label. Default: dev
  --data-region <region>         Region for data-plane services. Default: us-central1
  --batch-region <region>        Region for batch/orchestration services. Default: us-east1
  --api-region <region>          Region for Cloud Run API checks. Default: us-central1
  --api-service <name>           Cloud Run API service name. Default: get-flights-api
  --scheduler-job <name>         Scheduler job name. Default: daily-bts-pipeline
  --pubsub-topic <name>          Topic to validate. Default: bts-flights-rows
  --firestore-collection <name>  Firestore collection to probe. Default: flights_v1
  --dataset <name>               BigQuery dataset. Default: flighttracker_gold
  --fact-table <name>            BigQuery fact table. Default: fact_flights
  -h, --help                     Show this help message.

Outputs:
  - prints PASS / FAIL per check
  - exits with non-zero status if any check fails
EOF
}

log() {
  printf '[validate] %s\n' "$*"
}

pass() {
  printf 'PASS  %s\n' "$1"
}

fail_check() {
  printf 'FAIL  %s\n' "$1"
}

require_command() {
  local cmd="$1"
  command -v "${cmd}" >/dev/null 2>&1 || {
    printf '[validate] ERROR: Required command not found: %s\n' "${cmd}" >&2
    exit 1
  }
}

require_terraform_usable() {
  local output
  local status

  set +e
  output="$(terraform version 2>&1)"
  status=$?
  set -e

  if [[ ${status} -ne 0 ]] || grep -q "Follow the instructions at https://developer.hashicorp.com/terraform/install" <<<"${output}"; then
    printf '[validate] ERROR: Terraform CLI is not usable in this shell.\n' >&2
    exit 1
  fi
}

require_active_gcloud_account() {
  local active_account
  active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -n 1)"
  [[ -n "${active_account}" ]] || {
    printf '[validate] ERROR: No active gcloud account found.\n' >&2
    exit 1
  }
  log "Active gcloud account: ${active_account}"
}

run_check() {
  local label="$1"
  shift

  if "$@"; then
    pass "${label}"
  else
    fail_check "${label}"
    FAILURES=$((FAILURES + 1))
  fi
}

check_terraform_validate() {
  (
    cd "${TERRAFORM_DIR}"
    terraform validate >/dev/null
  )
}

fetch_api_url() {
  gcloud run services describe "${API_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${API_REGION}" \
    --format='value(status.url)'
}

check_api_health() {
  local api_url
  api_url="$(fetch_api_url)"
  [[ -n "${api_url}" ]] || return 1
  curl -fsS "${api_url}/health" | jq -e '.status == "healthy"' >/dev/null
}

check_api_flights() {
  local api_url
  api_url="$(fetch_api_url)"
  [[ -n "${api_url}" ]] || return 1
  curl -fsS "${api_url}/flights?limit=1" | jq -e '.status == "success" and (.count >= 0)' >/dev/null
}

check_api_live_flights() {
  local api_url
  api_url="$(fetch_api_url)"
  [[ -n "${api_url}" ]] || return 1
  curl -fsS "${api_url}/live/flights?limit=1" | jq -e '.status == "success" and (.count >= 0)' >/dev/null
}

check_pubsub_topic() {
  gcloud pubsub topics describe "${PUBSUB_TOPIC}" --project="${PROJECT_ID}" >/dev/null 2>&1
}

check_firestore_collection() {
  local access_token
  local url
  local response

  access_token="$(gcloud auth print-access-token)"
  url="https://firestore.googleapis.com/v1/projects/${PROJECT_ID}/databases/(default)/documents/${FIRESTORE_COLLECTION}?pageSize=1"
  response="$(curl -fsS -H "Authorization: Bearer ${access_token}" "${url}")"
  jq -e '.documents | type == "array"' >/dev/null <<<"${response}"
}

check_bigquery_fact() {
  local result
  result="$(bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false --format=json \
    "SELECT COUNT(*) AS total_rows FROM \`${PROJECT_ID}.${BIGQUERY_DATASET}.${BIGQUERY_FACT_TABLE}\`" 2>/dev/null)"
  jq -e 'length == 1 and (.[0].total_rows | tonumber) > 0' >/dev/null <<<"${result}"
}

check_latest_dataproc_job() {
  local output
  output="$(gcloud dataproc jobs list \
    --project="${PROJECT_ID}" \
    --region="${BATCH_REGION}" \
    --limit=1 \
    --format='value(reference.jobId,status.state)' 2>/dev/null || true)"
  [[ -n "${output}" ]]
}

check_scheduler_job() {
  gcloud scheduler jobs describe "${SCHEDULER_JOB}" \
    --project="${PROJECT_ID}" \
    --location="${BATCH_REGION}" >/dev/null 2>&1
}

check_dq_report_presence() {
  local required_files=(
    "${DQ_DIR}/results/bts_profile.json"
    "${DQ_DIR}/results/openflights_airlines_profile.json"
    "${DQ_DIR}/results/openflights_airports_profile.json"
    "${DQ_DIR}/results/opensky_profile.json"
    "${DQ_DIR}/results/dq_summary.csv"
  )
  local file

  for file in "${required_files[@]}"; do
    [[ -s "${file}" ]] || return 1
  done

  return 0
}

FAILURES=0
ENV_NAME="${DEFAULT_ENV}"
PROJECT_ID="${PROJECT_ID:-}"
DATA_REGION="${DATA_REGION:-${DEFAULT_DATA_REGION}}"
BATCH_REGION="${BATCH_REGION:-${DEFAULT_BATCH_REGION}}"
API_REGION="${API_REGION:-${DEFAULT_API_REGION}}"
API_SERVICE="${API_SERVICE:-${DEFAULT_API_SERVICE}}"
SCHEDULER_JOB="${SCHEDULER_JOB:-${DEFAULT_SCHEDULER_JOB}}"
PUBSUB_TOPIC="${PUBSUB_TOPIC:-${DEFAULT_PUBSUB_TOPIC}}"
FIRESTORE_COLLECTION="${FIRESTORE_COLLECTION:-${DEFAULT_FIRESTORE_COLLECTION}}"
BIGQUERY_DATASET="${BIGQUERY_DATASET:-${DEFAULT_BIGQUERY_DATASET}}"
BIGQUERY_FACT_TABLE="${BIGQUERY_FACT_TABLE:-${DEFAULT_BIGQUERY_TABLE}}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id)
      PROJECT_ID="${2:-}"
      shift 2
      ;;
    --env)
      ENV_NAME="${2:-}"
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
    --api-region)
      API_REGION="${2:-}"
      shift 2
      ;;
    --api-service)
      API_SERVICE="${2:-}"
      shift 2
      ;;
    --scheduler-job)
      SCHEDULER_JOB="${2:-}"
      shift 2
      ;;
    --pubsub-topic)
      PUBSUB_TOPIC="${2:-}"
      shift 2
      ;;
    --firestore-collection)
      FIRESTORE_COLLECTION="${2:-}"
      shift 2
      ;;
    --dataset)
      BIGQUERY_DATASET="${2:-}"
      shift 2
      ;;
    --fact-table)
      BIGQUERY_FACT_TABLE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf '[validate] ERROR: Unknown argument: %s\n' "$1" >&2
      exit 1
      ;;
  esac
done

[[ -n "${PROJECT_ID}" ]] || {
  printf '[validate] ERROR: PROJECT_ID is required. Pass --project-id.\n' >&2
  exit 1
}

require_command gcloud
require_command terraform
require_command curl
require_command jq
require_command bq
require_terraform_usable
require_active_gcloud_account

gcloud config set project "${PROJECT_ID}" >/dev/null

log "Environment label: ${ENV_NAME}"
log "Project id       : ${PROJECT_ID}"
log "Data region      : ${DATA_REGION}"
log "Batch region     : ${BATCH_REGION}"
log "API region       : ${API_REGION}"

run_check "terraform validate" check_terraform_validate
run_check "api health" check_api_health
run_check "api flights" check_api_flights
run_check "api live flights" check_api_live_flights
run_check "pubsub topic exists" check_pubsub_topic
run_check "firestore collection probe" check_firestore_collection
run_check "bigquery gold fact rows" check_bigquery_fact
run_check "latest dataproc job visible" check_latest_dataproc_job
run_check "scheduler job exists" check_scheduler_job
run_check "dq report presence" check_dq_report_presence

if [[ ${FAILURES} -gt 0 ]]; then
  log "Validation completed with ${FAILURES} failing check(s)."
  exit 1
fi

log "Validation completed successfully with all checks passing."
