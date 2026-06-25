# Raspberry Pi Dashboard

Simple web dashboard showing the integrated feeding-safety decision, Camera AI
state, contact-pad state, servo command, CSV status, and the latest annotated
camera frame. This is intended for SSH/Tailscale remote demo monitoring from a
browser.

## Install

```bash
pip install -r requirements.txt
```

## Run Dashboard Only

```bash
python raspberry_pi/dashboard/app.py \
  --log-dir data/logs \
  --log-file data/logs/feeding_decision_log.csv \
  --camera-log-file data/logs/camera_ai_log.csv \
  --debug-frame-dir data/debug_frames \
  --host 0.0.0.0 \
  --port 8080
```

Open `http://<pi-ip>:8080`.

The camera image appears after Camera AI writes:

```text
data/debug_frames/latest_camera_ai.jpg
```

## Run Camera AI + Dashboard

From the repository root:

```bash
./scripts/run_demo.sh
```

Defaults:

```text
RUN_CAMERA_AI=1
RUN_SAFETY_CONTROL=1
SAFETY_INPUT_MODE=camera
RUN_DASHBOARD=1
RUN_SERIAL_LOGGER=0
CAMERA_DEVICE=/dev/video0
DASHBOARD_PORT=8080
```

The safety-control process uses a mock contact input by default. It only
produces presentation decisions and never directly drives the physical servo.

For a hardware-free rehearsal:

```bash
RUN_CAMERA_AI=0 SAFETY_INPUT_MODE=scenario ./scripts/run_demo.sh
```

To also start the Arduino serial logger:

```bash
RUN_SERIAL_LOGGER=1 ./scripts/run_demo.sh
```
