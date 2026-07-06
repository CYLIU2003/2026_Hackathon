#!/usr/bin/env bash
set -euo pipefail

SERIAL_PORT="${SERIAL_PORT:-/dev/ttyACM0}"
BAUDRATE="${BAUDRATE:-115200}"
LOG_DIR="${LOG_DIR:-data/logs}"
CAMERA_DEVICE="${CAMERA_DEVICE:-auto}"
DASHBOARD_HOST="${DASHBOARD_HOST:-0.0.0.0}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8080}"
RUN_CAMERA_AI="${RUN_CAMERA_AI:-1}"
RUN_SAFETY_CONTROL="${RUN_SAFETY_CONTROL:-1}"
SAFETY_INPUT_MODE="${SAFETY_INPUT_MODE:-camera}"
RUN_SERIAL_LOGGER="${RUN_SERIAL_LOGGER:-0}"
RUN_DASHBOARD="${RUN_DASHBOARD:-1}"
RUN_ACTUATOR_BRIDGE="${RUN_ACTUATOR_BRIDGE:-0}"
ACTUATOR_BRIDGE_NO_SERIAL="${ACTUATOR_BRIDGE_NO_SERIAL:-0}"
ACTUATOR_BRIDGE_PROFILE="${ACTUATOR_BRIDGE_PROFILE:-release-stop}"
CAMERA_AI_MODEL="${CAMERA_AI_MODEL:-}"
CAMERA_AI_FALLBACK_ON_CRASH="${CAMERA_AI_FALLBACK_ON_CRASH:-1}"
ALLOW_NCNN_INFERENCE="${ALLOW_NCNN_INFERENCE:-0}"
CAMERA_APPLY_V4L2_CONTROLS="${CAMERA_APPLY_V4L2_CONTROLS:-1}"
CAMERA_V4L2_CONTROLS="${CAMERA_V4L2_CONTROLS:-brightness=0,gain=0,gamma=100,backlight_compensation=3,contrast=32,saturation=80,auto_exposure=3,exposure_dynamic_framerate=0}"
MOCK_CONTACT="${MOCK_CONTACT:-1}"
MOCK_IMPEDANCE_KOHM="${MOCK_IMPEDANCE_KOHM:-92.4}"
HONEY_AMOUNT_PERCENT="${HONEY_AMOUNT_PERCENT:-80}"
# Camera AI 推論 on/off。1=推論あり、0=カメラのみフェイルセーフ(HOLD)。
# 既定は「配置されている推論モデルに応じた自動判定」:
#  - models/yolo_bear.onnx があれば ONNX Runtime 推理が安定するので 1
#  - なければ NCNN が segfault する環境を想定し 0（カメラのみ）
# 明示的に切替えたい場合は RUN_CAMERA_AI_INFERENCE=1 / 0 を設定すること。
if [[ -z "${RUN_CAMERA_AI_INFERENCE:-}" ]]; then
  if [[ -f models/yolo_bear.onnx ]]; then
    RUN_CAMERA_AI_INFERENCE=1
    CAMERA_AI_MODEL="${CAMERA_AI_MODEL:-models/yolo_bear.onnx}"
  else
    RUN_CAMERA_AI_INFERENCE=0
  fi
fi
if [[ "${RUN_CAMERA_AI_INFERENCE}" == "1" && -z "${CAMERA_AI_MODEL}" && -f models/yolo_bear.onnx ]]; then
  CAMERA_AI_MODEL="models/yolo_bear.onnx"
fi
if [[ "${RUN_CAMERA_AI_INFERENCE}" == "1" && -z "${CAMERA_AI_MODEL}" && "${ALLOW_NCNN_INFERENCE}" != "1" ]]; then
  echo "Camera AI inference requested, but no ONNX model is configured."
  echo "  Falling back to camera-only fail-safe mode to avoid NCNN native crashes."
  echo "  Set CAMERA_AI_MODEL=... or ALLOW_NCNN_INFERENCE=1 to override."
  RUN_CAMERA_AI_INFERENCE=0
fi
if [[ -z "${PYTHON_BIN:-}" && -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python}"
fi

mkdir -p "${LOG_DIR}" data/debug_frames

RUN_DEMO_LOCK_FILE="${RUN_DEMO_LOCK_FILE:-${LOG_DIR}/run_demo.lock}"
RUN_DEMO_PID_FILE="${RUN_DEMO_PID_FILE:-${LOG_DIR}/run_demo.pid}"

if command -v flock >/dev/null 2>&1; then
  exec 9>"${RUN_DEMO_LOCK_FILE}"
  if ! flock -n 9; then
    existing_pid="$(cat "${RUN_DEMO_PID_FILE}" 2>/dev/null || true)"
    echo "Another run_demo.sh is already running${existing_pid:+ (pid ${existing_pid})}."
    echo "Stop that process before starting a new demo, so /dev/video0 is not opened twice."
    exit 2
  fi
fi
printf '%s\n' "$$" > "${RUN_DEMO_PID_FILE}"

child_pids=()

resolve_camera_device() {
  if [[ "${CAMERA_DEVICE}" != "auto" && "${CAMERA_DEVICE}" != "bsw500m" && "${CAMERA_DEVICE}" != "buffalo_bsw500m" ]]; then
    printf '%s\n' "${CAMERA_DEVICE}"
    return
  fi

  "${PYTHON_BIN}" -c 'from raspberry_pi.camera_ai.camera_capture import resolve_camera_source; print(resolve_camera_source({"device": "auto", "preferred_usb_vendor_id": "0411", "preferred_usb_product_id": "02da"}))' 2>/dev/null \
    || printf '%s\n' "/dev/video0"
}

apply_camera_controls() {
  local camera_device="${1:-${CAMERA_DEVICE}}"
  if [[ "${CAMERA_APPLY_V4L2_CONTROLS}" != "1" ]]; then
    return
  fi
  if [[ ! "${camera_device}" =~ ^/dev/video[0-9]+$ ]]; then
    return
  fi
  if ! command -v v4l2-ctl >/dev/null 2>&1; then
    echo "Skipping camera controls: v4l2-ctl is not installed."
    return
  fi

  echo "Applying camera controls on ${camera_device}..."
  if ! v4l2-ctl --device="${camera_device}" --set-ctrl="${CAMERA_V4L2_CONTROLS}"; then
    echo "Camera controls could not be applied; continuing with existing camera settings."
  fi
}

cleanup() {
  trap - EXIT INT TERM
  for pid in "${child_pids[@]}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
  rm -f "${RUN_DEMO_PID_FILE}"
}

stop_demo() {
  cleanup
  exit 0
}

trap cleanup EXIT
trap stop_demo INT TERM

if [[ "${RUN_CAMERA_AI}" == "1" ]]; then
  CAMERA_DEVICE_RESOLVED="$(resolve_camera_device)"
  apply_camera_controls "${CAMERA_DEVICE_RESOLVED}"
  echo "Starting Camera AI on ${CAMERA_DEVICE_RESOLVED} (requested ${CAMERA_DEVICE})..."
  camera_ai_inference_args=()
  if [[ "${RUN_CAMERA_AI_INFERENCE}" != "1" ]]; then
    echo "  (inference disabled: camera-only fail-safe mode)"
    camera_ai_inference_args+=(--no-inference)
  elif [[ -n "${CAMERA_AI_MODEL}" ]]; then
    echo "  (model: ${CAMERA_AI_MODEL})"
    camera_ai_inference_args+=(--model "${CAMERA_AI_MODEL}")
  fi
  (
    set +e
    while true; do
      runtime_camera_device="$(resolve_camera_device)"
      "${PYTHON_BIN}" -m raspberry_pi.camera_ai.run_camera_ai \
        --device "${runtime_camera_device}" \
        --terminal-status \
        --no-jsonl \
        --save-debug-frames \
        "${camera_ai_inference_args[@]}"
      camera_ai_status=$?
      if [[ "${camera_ai_status}" -eq 0 ]]; then
        exit 0
      fi

      if [[ "${RUN_CAMERA_AI_INFERENCE}" == "1" && "${CAMERA_AI_FALLBACK_ON_CRASH}" == "1" ]]; then
        echo "Camera AI exited with status ${camera_ai_status}; trying camera-only fail-safe mode."
        "${PYTHON_BIN}" -m raspberry_pi.camera_ai.run_camera_ai \
          --device "${runtime_camera_device}" \
          --terminal-status \
          --no-jsonl \
          --save-debug-frames \
          --no-inference
        camera_ai_status=$?
        if [[ "${camera_ai_status}" -eq 0 ]]; then
          exit 0
        fi
      fi

      echo "Camera AI exited with status ${camera_ai_status}; retrying in 2s."
      sleep 2
      apply_camera_controls "$(resolve_camera_device)"
    done
  ) >> "${LOG_DIR}/camera_ai.status.log" 2>&1 &
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

if [[ "${RUN_ACTUATOR_BRIDGE}" == "1" ]]; then
  echo "Starting safety-to-actuator bridge on ${SERIAL_PORT}..."
  actuator_bridge_args=()
  if [[ "${ACTUATOR_BRIDGE_NO_SERIAL}" == "1" ]]; then
    actuator_bridge_args+=(--no-serial)
  fi
  "${PYTHON_BIN}" -m raspberry_pi.integration.safety_to_actuator \
    --input "${LOG_DIR}/feeding_decision_log.csv" \
    --port "${SERIAL_PORT}" \
    --baudrate "${BAUDRATE}" \
    --command-profile "${ACTUATOR_BRIDGE_PROFILE}" \
    "${actuator_bridge_args[@]}" \
    >> "${LOG_DIR}/actuator_bridge.status.log" 2>&1 &
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
