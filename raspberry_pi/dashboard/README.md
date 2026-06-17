# Raspberry Pi Dashboard

Simple web dashboard showing the latest contact-pad state, Camera AI state, and
the latest annotated camera frame. This is intended for SSH/Tailscale remote
demo monitoring from a browser.

## Install

```bash
pip install -r requirements.txt
```

## Run Dashboard Only

```bash
python raspberry_pi/dashboard/app.py \
  --log-dir data/logs \
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
RUN_DASHBOARD=1
RUN_SERIAL_LOGGER=0
CAMERA_DEVICE=/dev/video0
DASHBOARD_PORT=8080
```

To also start the Arduino serial logger:

```bash
RUN_SERIAL_LOGGER=1 ./scripts/run_demo.sh
```
