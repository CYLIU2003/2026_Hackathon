# Raspberry Pi Modules

This directory contains the Raspberry Pi side of the demo: camera AI, logging,
dashboard, and remote monitoring.

## Module Index

| Module | Purpose | Main command |
|---|---|---|
| `camera_ai/` | USB camera capture, YOLO inference, AI state logging, model tooling | `python -m raspberry_pi.camera_ai.run_camera_ai --device /dev/video0 --terminal-status --no-jsonl` |
| `safety_control/` | Camera + mock contact decision mirror and unified CSV | `python -m raspberry_pi.safety_control.safety_controller --input-mode camera` |
| `integration/safety_to_actuator.py` | Bridges `RELEASE_ON/OFF` from the safety CSV to Arduino serial commands | `python -m raspberry_pi.integration.safety_to_actuator --input data/logs/feeding_decision_log.csv --port /dev/ttyACM0` |
| `camera_ai/web_camera_ai.py` | Live browser view over SSH port forwarding | `python raspberry_pi/camera_ai/web_camera_ai.py --device /dev/video0 --host 127.0.0.1 --port 8081` |
| `dashboard/` | Browser dashboard for latest logs and debug camera image | `python raspberry_pi/dashboard/app.py --log-dir data/logs --host 0.0.0.0 --port 8080` |
| `logger/` | Serial JSON Lines to CSV logger for Arduino Uno | `python raspberry_pi/logger/serial_logger.py --serial-port /dev/ttyACM0` |

## Recommended Feeding Decision Demo

From the repository root on the Raspberry Pi:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/camera_ai/requirements.txt
python -m pip install -r raspberry_pi/dashboard/requirements.txt
./scripts/run_demo.sh
```

The command starts Camera AI, the mock contact safety-decision mirror, and the
dashboard. The integrated CSV is written to:

```text
data/logs/feeding_decision_log.csv
```

This prototype uses simulated sensor inputs. The Raspberry Pi decision is for
presentation and integration testing; Arduino Uno Q remains the authoritative
physical safety controller.

To run the full venue path from camera recognition through Arduino mechanism
motion, connect the Arduino over USB and start:

```bash
RUN_CAMERA_AI_INFERENCE=1 RUN_ACTUATOR_BRIDGE=1 ./scripts/run_demo.sh
```

The actuator bridge sends `RELEASE` only when the latest safety CSV row is fresh
and says `RELEASE_ON`. Missing/stale data, `ERROR_SAFE`, or emergency stop keeps
the bridge on `STOP`.

For Haruka GODA's direct-servo sketch
`Haruka GODA/beehivemotorC++/0to90/0to90.ino`, upload that sketch to Arduino Uno,
connect the servo signal to D3, power the servo from an external 5V-6V supply
with common GND, then run:

```bash
RUN_CAMERA_AI_INFERENCE=1 \
RUN_ACTUATOR_BRIDGE=1 \
ACTUATOR_BRIDGE_PROFILE=goda-state \
SERIAL_PORT=/dev/ttyACM0 \
./scripts/run_demo.sh
```

`goda-state` sends the latest CSV safety fields as `SET AI_BEAR`, `SET PAW`,
`SET HONEY`, `SET SAFE`, and `SET ESTOP`. The Arduino sketch still checks those
conditions, confirms contact, applies cooldown, and defaults to closed /
`RELEASE_OFF`.

Open the dashboard:

```text
http://<pi-ip>:8080
```

## SSH Live Viewer

On the Raspberry Pi:

```bash
source .venv/bin/activate
python raspberry_pi/camera_ai/web_camera_ai.py \
  --device /dev/video0 \
  --host 127.0.0.1 \
  --port 8081 \
  --terminal-status
```

On this PC:

```powershell
ssh -L 8081:127.0.0.1:8081 <pi-ssh-host>
```

Open:

```text
http://127.0.0.1:8081
```

## Detailed Docs

- Camera AI: `raspberry_pi/camera_ai/README.md`
- Dashboard: `raspberry_pi/dashboard/README.md`
- Logger: `raspberry_pi/logger/README.md`
- Feature overview: `docs/feature_overview.md`
- Repository map: `docs/repository_map.md`
