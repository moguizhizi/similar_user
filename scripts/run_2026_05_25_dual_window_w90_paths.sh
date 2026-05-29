#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

BASE_DATE="${BASE_DATE:-2026-05-25}"
PATIENT_IDS_FILE="${PATIENT_IDS_FILE:-data/patient_ids/base_2026-05-25/patients_active_2026-05-25.txt}"
PATIENT_LIMIT="${PATIENT_LIMIT:-100}"
CONFIG_PATH="${CONFIG_PATH:-config/settings_window_90.yaml}"
LOG_DIR="${LOG_DIR:-logs/monthly_pattern_paths_w90}"

QUERY_FAMILIES=(
  "training_order_dual_window"
  "training_order_age_dual_window"
)

mkdir -p "${LOG_DIR}"

failed_count=0

echo "[$(date '+%F %T')] Start monthly pattern path batch"
echo "base_date=${BASE_DATE}"
echo "patient_ids_file=${PATIENT_IDS_FILE}"
echo "patient_limit=${PATIENT_LIMIT}"
echo "config=${CONFIG_PATH}"
echo "log_dir=${LOG_DIR}"

for qf in "${QUERY_FAMILIES[@]}"; do
  log_path="${LOG_DIR}/run_monthly_pattern_paths_${BASE_DATE}_${qf}_w90.log"
  echo "[$(date '+%F %T')] Start query_family=${qf}, log=${log_path}"

  python scripts/run_monthly_pattern_paths.py \
    --base-date "${BASE_DATE}" \
    --patient-ids-file "${PATIENT_IDS_FILE}" \
    --patient-limit "${PATIENT_LIMIT}" \
    --query-family "${qf}" \
    --config "${CONFIG_PATH}" \
    > "${log_path}" 2>&1

  rc=$?
  if [[ "${rc}" -eq 0 ]]; then
    echo "[$(date '+%F %T')] Done query_family=${qf}"
  else
    failed_count=$((failed_count + 1))
    echo "[$(date '+%F %T')] Failed query_family=${qf}, exit_code=${rc}, continue"
  fi
done

if [[ "${failed_count}" -gt 0 ]]; then
  echo "[$(date '+%F %T')] Completed with ${failed_count} failed query families"
  exit 1
fi

echo "[$(date '+%F %T')] Completed all query families"
