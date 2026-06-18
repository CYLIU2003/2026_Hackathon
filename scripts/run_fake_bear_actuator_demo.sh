#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-/dev/ttyACM0}"

python3 raspberry_pi/integration/fake_bear_to_actuator.py \
  --port "${PORT}" \
  --loop
