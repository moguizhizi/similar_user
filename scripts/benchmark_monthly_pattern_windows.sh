#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

BASE_DATE="${BASE_DATE:-2026-05-25}"
PATIENT_IDS_FILE="${PATIENT_IDS_FILE:-data/patient_ids/base_2026-05-25/patients_active_2026-05-25.txt}"
PATIENT_LIMIT="${PATIENT_LIMIT:-500}"
REPEAT="${REPEAT:-1}"
BENCHMARK_ROOT="${BENCHMARK_ROOT:-logs/monthly_pattern_paths_benchmark}"
SUMMARY_PATH="${SUMMARY_PATH:-data/benchmarks/monthly_pattern_paths_speed_${BASE_DATE}.tsv}"

WINDOWS_TEXT="${WINDOWS:-14 28 45 90}"
QUERY_FAMILIES_TEXT="${QUERY_FAMILIES:-training_order_dual_window}"

read -r -a WINDOWS_ARRAY <<< "${WINDOWS_TEXT}"
read -r -a QUERY_FAMILIES_ARRAY <<< "${QUERY_FAMILIES_TEXT}"

mkdir -p "${BENCHMARK_ROOT}"
mkdir -p "$(dirname "${SUMMARY_PATH}")"

if [[ ! -f "${PATIENT_IDS_FILE}" ]]; then
  echo "Patient ID file not found: ${PATIENT_IDS_FILE}" >&2
  exit 1
fi

if [[ ! "${REPEAT}" =~ ^[0-9]+$ ]] || [[ "${REPEAT}" -le 0 ]]; then
  echo "REPEAT must be a positive integer: ${REPEAT}" >&2
  exit 1
fi

if [[ ! -f "${SUMMARY_PATH}" ]]; then
  printf "run_id\tbase_date\twindow_days\tquery_family\tpatient_limit\texit_code\telapsed_sec\tstarted_at\tfinished_at\tconfig_path\tlog_path\n" \
    > "${SUMMARY_PATH}"
fi

failed_count=0

echo "[$(date '+%F %T')] Start monthly pattern path window benchmark"
echo "base_date=${BASE_DATE}"
echo "patient_ids_file=${PATIENT_IDS_FILE}"
echo "patient_limit=${PATIENT_LIMIT}"
echo "repeat=${REPEAT}"
echo "windows=${WINDOWS_TEXT}"
echo "query_families=${QUERY_FAMILIES_TEXT}"
echo "benchmark_root=${BENCHMARK_ROOT}"
echo "summary_path=${SUMMARY_PATH}"

for run_id in $(seq 1 "${REPEAT}"); do
  for window_days in "${WINDOWS_ARRAY[@]}"; do
    config_path="config/settings_window_${window_days}.yaml"
    if [[ ! -f "${config_path}" ]]; then
      echo "[$(date '+%F %T')] Missing config for window=${window_days}: ${config_path}" >&2
      failed_count=$((failed_count + 1))
      continue
    fi

    for query_family in "${QUERY_FAMILIES_ARRAY[@]}"; do
      run_log_dir="${BENCHMARK_ROOT}/w${window_days}/${query_family}/run_${run_id}"
      mkdir -p "${run_log_dir}"
      log_path="${run_log_dir}/run_monthly_pattern_paths_${BASE_DATE}.log"

      started_at="$(date '+%F %T')"
      start_ts="$(date +%s)"
      echo "[$started_at] Start run=${run_id}, window=${window_days}, query_family=${query_family}, log=${log_path}"

      python scripts/run_monthly_pattern_paths.py \
        --base-date "${BASE_DATE}" \
        --patient-ids-file "${PATIENT_IDS_FILE}" \
        --patient-limit "${PATIENT_LIMIT}" \
        --query-family "${query_family}" \
        --config "${config_path}" \
        --log-dir "${run_log_dir}/patients" \
        > "${log_path}" 2>&1

      rc=$?
      end_ts="$(date +%s)"
      finished_at="$(date '+%F %T')"
      elapsed_sec=$((end_ts - start_ts))

      printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "${run_id}" \
        "${BASE_DATE}" \
        "${window_days}" \
        "${query_family}" \
        "${PATIENT_LIMIT}" \
        "${rc}" \
        "${elapsed_sec}" \
        "${started_at}" \
        "${finished_at}" \
        "${config_path}" \
        "${log_path}" \
        >> "${SUMMARY_PATH}"

      if [[ "${rc}" -eq 0 ]]; then
        echo "[$finished_at] Done run=${run_id}, window=${window_days}, query_family=${query_family}, elapsed_sec=${elapsed_sec}"
      else
        failed_count=$((failed_count + 1))
        echo "[$finished_at] Failed run=${run_id}, window=${window_days}, query_family=${query_family}, exit_code=${rc}, elapsed_sec=${elapsed_sec}, continue"
      fi
    done
  done
done

if [[ "${failed_count}" -gt 0 ]]; then
  echo "[$(date '+%F %T')] Completed with ${failed_count} failed benchmark runs"
  exit 1
fi

echo "[$(date '+%F %T')] Completed all benchmark runs"
