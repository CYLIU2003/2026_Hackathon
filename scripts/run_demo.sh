#!/usr/bin/env bash
set -euo pipefail

SERIAL_PORT="${SERIAL_PORT:-/dev/ttyACM0}"
BAUDRATE="${BAUDRATE:-115200}"
LOG_DIR="${LOG_DIR:-data/logs}"
CAMERA_DEVICE="${CAMERA_DEVICE:-/dev/video0}"
DASHBOARD_HOST="${DASHBOARD_HOST:-0.0.0.0}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8080}"
RUN_CAMERA_AI="${RUN_CAMERA_AI:-1}"
RUN_SAFETY_CONTROL="${RUN_SAFETY_CONTROL:-1}"
SAFETY_INPUT_MODE="${SAFETY_INPUT_MODE:-camera}"
RUN_SERIAL_LOGGER="${RUN_SERIAL_LOGGER:-0}"
RUN_DASHBOARD="${RUN_DASHBOARD:-1}"
MOCK_CONTACT="${MOCK_CONTACT:-1}"
MOCK_IMPEDANCE_KOHM="${MOCK_IMPEDANCE_KOHM:-92.4}"
HONEY_AMOUNT_PERCENT="${HONEY_AMOUNT_PERCENT:-80}"
if [[ -z "${PYTHON_BIN:-}" && -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python}"
fi

mkdir -p "${LOG_DIR}" data/debug_frames

child_pids=()

cleanup() {
  trap - EXIT INT TERM
  for pid in "${child_pids[@]}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}

stop_demo() {
  cleanup
  exit 0
}

trap cleanup EXIT
trap stop_demo INT TERM

if [[ "${RUN_CAMERA_AI}" == "1" ]]; then
  echo "Starting Camera AI on ${CAMERA_DEVICE}..."
  "${PYTHON_BIN}" -m raspberry_pi.camera_ai.run_camera_ai \
    --device "${CAMERA_DEVICE}" \
    --terminal-status \
    --no-jsonl \
    --save-debug-frames \
    >> "${LOG_DIR}/camera_ai.status.log" 2>&1 &
  child_pids+=("$!")
fi

if [[ "${RUN_SAFETY_CONTROL}" == "1" ]]; then
  echo "Starting feeding safety decision mirror..."
  safety_contact_arg="--no-mock-contact"
  if [[ "${MOCK_CONTACT}" == "1" ]]; then
    safety_contact_arg="--mock-contact"
  fi
  "${PYTHON_BIN}" -m raspberry_pi.safety_control.safety_controller \
    --input-mode "${SAFETY_INPUT_MODE}" \
    --camera-log-file "${LOG_DIR}/camera_ai_log.csv" \
    --output "${LOG_DIR}/feeding_decision_log.csv" \
    "${safety_contact_arg}" \
    --mock-impedance-kohm "${MOCK_IMPEDANCE_KOHM}" \
    --honey-amount-percent "${HONEY_AMOUNT_PERCENT}" \
    >> "${LOG_DIR}/safety_control.status.log" 2>&1 &
  child_pids+=("$!")
fi

if [[ "${RUN_SERIAL_LOGGER}" == "1" ]]; then
  echo "Starting serial logger on ${SERIAL_PORT}..."
  "${PYTHON_BIN}" raspberry_pi/logger/serial_logger.py \
    --serial-port "${SERIAL_PORT}" \
    --baudrate "${BAUDRATE}" \
    --log-dir "${LOG_DIR}" \
    >> "${LOG_DIR}/serial_logger.status.log" 2>&1 &
  child_pids+=("$!")
fi

if [[ "${RUN_DASHBOARD}" == "1" ]]; then
  echo "Starting dashboard on http://${DASHBOARD_HOST}:${DASHBOARD_PORT}"
  "${PYTHON_BIN}" raspberry_pi/dashboard/app.py \
    --log-dir "${LOG_DIR}" \
    --log-file "${LOG_DIR}/feeding_decision_log.csv" \
    --camera-log-file "${LOG_DIR}/camera_ai_log.csv" \
    --debug-frame-dir data/debug_frames \
    --demo-serial-port "${SERIAL_PORT}" \
    --demo-baudrate "${BAUDRATE}" \
    --demo-command-log-file "${LOG_DIR}/demo_commands.csv" \
    --host "${DASHBOARD_HOST}" \
    --port "${DASHBOARD_PORT}" &
  child_pids+=("$!")
fi

echo "Remote dashboard URL: http://<pi-ip>:${DASHBOARD_PORT}"
echo "Press Ctrl+C to stop the demo processes."
wait
