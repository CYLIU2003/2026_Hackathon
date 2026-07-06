# Raspberry Pi Dashboard

Simple web dashboard showing the integrated feeding-safety decision, Camera AI
state, contact-pad state, servo command, CSV status, and a live MJPEG view of
the latest annotated camera frames. This is intended for SSH/Tailscale remote
demo monitoring from a browser.

The first screen prioritizes `Camera AI View` and `Camera AI State`, followed by
the integrated feeding-safety decision and demo controls.

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

For remote operation, open the same dashboard through the Raspberry Pi Tailscale
address. The Arduino remains connected to the Raspberry Pi by wired USB serial;
the dashboard does not assume the Arduino has Wi-Fi.

The camera stream appears after Camera AI writes:

```text
data/debug_frames/latest_camera_ai.jpg
```

The dashboard serves that updated frame as `/camera/stream.mjpg`, so the camera
view can remain live while Camera AI inference runs at a slower interval.
If the latest frame is almost black, the dashboard marks it as `FRAME DARK` and
shows the measured frame brightness.

## Demo Mode

The dashboard includes a manual Demo Mode panel for presentation use.

- Default state is `STOP` / closed.
- Demo Mode must be enabled before `Release / Open` or `Test Motion` commands
  are accepted.
- `Stop / Close` and `Emergency Stop` are always available and send `STOP`.
- The Raspberry Pi backend sends only simple USB serial command strings to the
  Arduino: `RELEASE`, `STOP`, and `TEST`.
- If the Arduino serial port is unavailable, the same UI runs in simulation
  mode and logs the command without controlling hardware.

Command log:

```text
data/logs/demo_commands.csv
```

Useful hardware run options:

```bash
python raspberry_pi/dashboard/app.py \
  --demo-serial-port /dev/ttyACM0 \
  --demo-baudrate 115200 \
  --demo-command-log-file data/logs/demo_commands.csv
```

Hardware-free rehearsal:

```bash
python raspberry_pi/dashboard/app.py --demo-force-simulation
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
