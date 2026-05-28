#!/usr/bin/env bash
set -euo pipefail

BASE_DATE="2026-05-25"
PATIENT_IDS_FILE="data/patient_ids/base_2026-05-25/patients_active_2026-05-25.txt"

QUERY_FAMILIES=(
  "training_order_age_only_source_window"
  "training_order_layer1_age_completion_source_window"
  "training_order_layer2_education_exact_source_window"
  "training_order_layer3_activity_task_type_source_window"
)

failed_count=0

for qf in "${QUERY_FAMILIES[@]}"; do
  echo "[$(date '+%F %T')] Start query_family=${qf}"

  if python scripts/run_monthly_pattern_paths.py \
    --base-date "${BASE_DATE}" \
    --patient-ids-file "${PATIENT_IDS_FILE}" \
    --query-family "${qf}"; then
    echo "[$(date '+%F %T')] Done query_family=${qf}"
  else
    failed_count=$((failed_count + 1))
    echo "[$(date '+%F %T')] Failed query_family=${qf}, continue"
  fi
done

if [[ "${failed_count}" -gt 0 ]]; then
  echo "[$(date '+%F %T')] Completed with ${failed_count} failed query families"
  exit 1
fi

echo "[$(date '+%F %T')] Completed all query families"
