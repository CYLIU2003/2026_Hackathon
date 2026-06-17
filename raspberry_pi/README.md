# Raspberry Pi Modules

This directory contains the Raspberry Pi side of the demo: camera AI, logging,
dashboard, and remote monitoring.

## Module Index

| Module | Purpose | Main command |
|---|---|---|
| `camera_ai/` | USB camera capture, YOLO inference, AI state logging, model tooling | `python -m raspberry_pi.camera_ai.run_camera_ai --device /dev/video0 --terminal-status --no-jsonl` |
| `camera_ai/web_camera_ai.py` | Live browser view over SSH port forwarding | `python raspberry_pi/camera_ai/web_camera_ai.py --device /dev/video0 --host 127.0.0.1 --port 8081` |
| `dashboard/` | Browser dashboard for latest logs and debug camera image | `python raspberry_pi/dashboard/app.py --log-dir data/logs --host 0.0.0.0 --port 8080` |
| `logger/` | Serial JSON Lines to CSV logger for Arduino Uno Q | `python raspberry_pi/logger/serial_logger.py --serial-port /dev/ttyACM0` |

## Recommended Demo

From the repository root on the Raspberry Pi:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/camera_ai/requirements.txt
python -m pip install -r raspberry_pi/dashboard/requirements.txt
./scripts/run_demo.sh
```

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
