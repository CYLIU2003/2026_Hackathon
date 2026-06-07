#!/usr/bin/env bash
set -euo pipefail

SERIAL_PORT="${SERIAL_PORT:-/dev/ttyACM0}"
BAUDRATE="${BAUDRATE:-115200}"
LOG_DIR="${LOG_DIR:-data/logs}"

echo "Starting serial logger on ${SERIAL_PORT}..."
python raspberry_pi/logger/serial_logger.py --serial-port "${SERIAL_PORT}" --baudrate "${BAUDRATE}" --log-dir "${LOG_DIR}"
