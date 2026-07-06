# A1 Front Paw Contact Pad System

## Overview

This repository contains the prototype for the **Front Paw Contact Pad System** in the A1 **Bear Honey Buffet** hackathon project.

The current prototype now includes both simulated/contact-pad control and a Raspberry Pi camera AI module. The goal is to detect whether a bear or target object is approaching, confirm front paw contact or future electrical-resistance/contact-pad input, check honey and safety conditions, and then safely decide whether to send a honey release signal.

Camera AI is an additional perception layer, not the only safety controller. YOLO detection must not directly trigger honey release.

The first control version can still run with **simulated sensor inputs**. The conventional Arduino/contact-pad and electrical-resistance confirmation path remains in the repository and will be integrated separately later.

---

## Quick Navigation

| Need | Start here |
|---|---|
| Understand the current feature set | `docs/feature_overview.md` |
| Find where files belong | `docs/repository_map.md` |
| Run Raspberry Pi camera AI | `raspberry_pi/camera_ai/README.md` |
| Run Raspberry Pi dashboard/logger | `raspberry_pi/README.md` |
| Check safety/interface contracts | `docs/interface_spec.md`, `docs/camera_ai_interface_spec.md` |
| Work on Arduino contact-pad logic | `arduino_uno_q/contact_pad_controller/` |

---

## Project Vision

The whole A1 system is divided into four layers.

```text
[Bear]
  ↓
[Camera AI perception layer]
  ↓ ai_bear_approaching
[Contact / resistance confirmation layer]
  ↓ paw_contact / raw_contact_value
[Safety decision layer]
  ↓ RELEASE_ON / RELEASE_OFF
[Honey release actuator layer]
  ↓
[Honey release mechanism]
```

This repository focuses on perception, contact confirmation, safety decision logic, logging, and demo support. The honey release actuator side is represented as a simple RELEASE_ON/OFF interface and later PCA9685 + servo integration.

---

## What This System Does

The system checks:

```text
1. Is a bear or target object approaching?           ai_bear_approaching / bear_detected
2. Is the front paw touching the pad?                paw_contact / raw_contact_value
3. Is there enough honey?                            honey_amount_percent
4. Is the system safe?                               system_safe
5. Is emergency stop inactive?                       emergency_stop == false
6. Should the honey release mechanism be activated?  RELEASE_ON / RELEASE_OFF
```

If all conditions are satisfied, the system outputs:

```text
RELEASE_ON
```

Otherwise, it outputs:

```text
RELEASE_OFF
```

---

## Hardware Concept

### Arduino Uno

Arduino Uno remains the field-side contact and safety controller.

Expected responsibilities:

```text
- contact pad input
- future electrical-resistance/contact measurement
- simulated sensor input
- threshold judgement
- release decision logic
- LED / GPIO / release signal output
- USB serial communication
```

Arduino Uno / electrical-resistance measurement / contact-pad logic must remain documented and implemented. The camera AI layer can add `ai_bear_approaching`, but it does not replace `paw_contact`, `raw_contact_value`, contact thresholds, emergency stop, or RELEASE_OFF fail-safe behavior.

For the PCA9685 actuator, connect `SDA` to Arduino Uno `A4`, `SCL` to `A5`,
`VCC` to logic power, and all grounds together. Power the servo from a suitable
external supply, not from the Uno 5V pin.

### Raspberry Pi 4B

Raspberry Pi 4B 4GB is used for AI camera recognition, logging, and upper-level state handling.

Expected responsibilities:

```text
- capture images from BUFFALO BSW500M USB camera
- run OpenCV / V4L2 camera capture
- run lightweight YOLO bear approach detection
- publish ai_bear_approaching state
- receive data from Arduino Uno
- save CSV logs
- show dashboard
- visualize latest state
- support presentation demo
- remote access by SSH/Tailscale
```

The Raspberry Pi should not be the only safety controller. Camera AI is an additional perception layer, not the only safety controller.

### BUFFALO BSW500M USB Camera

The BUFFALO BSW500M USB web camera is connected to the Raspberry Pi 4B.

```text
- USB ID: 0411:02da
- /dev/video0: actual image stream device
- /dev/video1: metadata device, not for image capture
- default config: device=auto, preferring the 0411:02da Video Capture node and skipping metadata nodes
- if OpenCV cannot open the /dev/video0 path, it automatically falls back to the matching index 0
- recommended FourCC: MJPG first, then YUYV fallback
- recommended resolution: 640x480 first, then 320x240 fallback
```

### PCA9685 + Servo Motor

PCA9685 + servo motor + external power supply are used on the honey release mechanism side.

```text
- input: RELEASE_ON / RELEASE_OFF
- role: actuator drive for honey release demo mechanism
- safety: no uncontrolled release; RELEASE_OFF remains the default
```

---

## System Architecture

```text
Bear / target object
  ↓
BUFFALO BSW500M USB Camera
  ↓
Raspberry Pi 4B 4GB
  - OpenCV / V4L2 camera capture
  - YOLO bear detection
  - bear approach judgement
  - JSON Lines / CSV logging
  ↓
Existing decision logic
  - ai_bear_approaching
  - paw_contact / resistance measurement
  - honey_amount_percent
  - system_safe
  - emergency_stop
  ↓
RELEASE_ON / RELEASE_OFF
  ↓
PCA9685 + Servo Motor
  ↓
Honey release mechanism
```

---

## MVP v0.1

The first MVP should demonstrate the following.

### Input

```text
simulated_bear_detected
ai_bear_approaching
simulated_paw_contact
raw_contact_value
simulated_honey_amount_percent
simulated_system_safe
emergency_stop
```

### Logic

```text
release_allowed = (
    ai_bear_approaching
    and paw_contact
    and honey_amount_percent >= honey_min_threshold_percent
    and system_safe
    and not emergency_stop
)
```

### Output

```text
- RELEASE_ON / RELEASE_OFF
- LED ON/OFF
- JSON Lines over serial
- CSV log on Raspberry Pi
- Camera AI JSON Lines / CSV state
```

---

## State Machine

```text
IDLE
  ↓ bear detected
BEAR_DETECTED
  ↓ paw contact confirmed
CONTACT_CONFIRMED
  ↓ honey enough and system safe
READY_TO_RELEASE
  ↓ release command
RELEASING
  ↓ timeout
COOLDOWN
  ↓ cooldown finished
IDLE
```

Error handling:

```text
ANY_STATE
  ↓ invalid data / emergency stop / communication error
ERROR_SAFE
  ↓ RESET command
IDLE
```

In `ERROR_SAFE`, release must always be OFF.

---

## Safety Policy

This project is a hackathon prototype.  
It must not harm animals or people.

Do not:

```text
- use high voltage/current on a contact pad
- design an electric shock system
- test on real bears without expert supervision
- claim real bear resistance values without valid measurement
- allow uncontrolled honey release
```

Always:

```text
- default to RELEASE_OFF
- use simulated inputs first
- keep camera AI as an additional perception layer, not the only safety controller
- never allow YOLO detection alone to trigger honey release
- keep release duration limited
- log every important state change
- separate contact pad logic from honeycomb mechanism
```

Honey release is allowed only when all required conditions are satisfied:

```python
release_allowed = (
    ai_bear_approaching
    and paw_contact
    and honey_amount_percent >= honey_min_threshold_percent
    and system_safe
    and not emergency_stop
)
```

---

## Data Format

Arduino Uno should send JSON Lines.

Example:

```json
{"timestamp":"2026-05-23T18:30:00+09:00","bear_detected":false,"paw_contact":false,"honey_amount_percent":80,"system_safe":true,"emergency_stop":false,"release_state":"RELEASE_OFF","state":"IDLE","event":"IDLE"}
{"timestamp":"2026-05-23T18:30:05+09:00","bear_detected":true,"paw_contact":true,"honey_amount_percent":80,"system_safe":true,"emergency_stop":false,"release_state":"RELEASE_ON","state":"RELEASING","event":"RELEASE_START"}
```

Raspberry Pi should save CSV logs.

Example:

```csv
timestamp,bear_detected,paw_contact,honey_amount_percent,system_safe,emergency_stop,release_state,state,event
2026-05-23T18:30:00+09:00,false,false,80,true,false,RELEASE_OFF,IDLE,IDLE
2026-05-23T18:30:05+09:00,true,true,80,true,false,RELEASE_ON,RELEASING,RELEASE_START
```

Camera AI also emits JSON Lines from Raspberry Pi:

```json
{"source":"camera_ai","ai_camera_ok":true,"ai_model_ok":true,"ai_bear_detected":true,"ai_bear_confidence":0.82,"ai_bear_box_area_ratio":0.18,"ai_bear_approaching":true,"event":"AI_BEAR_APPROACHING"}
```

These camera AI fields are inputs to the safety decision layer only. They do not directly command `RELEASE_ON`.

---

## Recommended Repository Layout

```text
a1-front-paw-contact-pad/
├─ README.md
├─ README.ja.md
├─ README.zh-CN.md
├─ README.ko.md
├─ AGENTS.md
├─ AI_DEVELOPMENT_INSTRUCTIONS.md
├─ VARIABLES.md
├─ PROJECT_GUARDRAILS.md
├─ docs/
│  ├─ block_diagram.md
│  ├─ state_machine.md
│  ├─ interface_spec.md
│  ├─ camera_ai_design.md
│  ├─ camera_ai_interface_spec.md
│  ├─ feature_overview.md
│  └─ repository_map.md
├─ arduino_uno_q/
│  ├─ contact_pad_controller/
│  │  ├─ contact_pad_controller.ino
│  │  └─ config.h
│  └─ README.md
├─ raspberry_pi/
│  ├─ camera_ai/
│  │  ├─ run_camera_ai.py
│  │  ├─ web_camera_ai.py
│  │  ├─ camera_test.py
│  │  ├─ camera_capture.py
│  │  ├─ bear_detector.py
│  │  ├─ approach_logic.py
│  │  ├─ prepare_bear_training_data.py
│  │  ├─ train_bear_yolo.py
│  │  ├─ export_lightweight_yolo.py
│  │  ├─ import_colab_artifacts.py
│  │  ├─ package_pi_camera_ai.py
│  │  └─ config.camera_ai.yaml
│  ├─ logger/
│  │  ├─ serial_logger.py
│  │  └─ requirements.txt
│  ├─ dashboard/
│  │  ├─ app.py
│  │  └─ requirements.txt
│  └─ README.md
├─ data/
│  └─ logs/
├─ models/
│  ├─ yolo_bear_ncnn_model/
│  └─ yolo_bear.pt
├─ notebooks/
│  └─ colab_bear_yolo_training.ipynb
├─ outputs/
│  └─ camera_test.jpg
├─ examples/
│  └─ sample_log.csv
└─ scripts/
   └─ run_demo.sh
```

`models/` and `outputs/` are runtime/demo folders. Runtime model files under
`models/yolo_bear_ncnn_model` and `models/yolo_bear.pt` may be committed
intentionally for Raspberry Pi transfer. Generated camera images, logs, raw
training datasets, and Colab byproducts should stay out of Git.

---

## Camera AI Module

The camera AI module runs on Raspberry Pi 4B 4GB with a BUFFALO BSW500M USB web camera.

Camera AI is an additional perception layer, not the only safety controller.
The remote browser view is for monitoring and demo support only; it does not
move the RELEASE_ON/OFF safety decision away from the Arduino/contact-pad side.

Hardware and runtime assumptions:

```text
- Target device: Raspberry Pi 4B 4GB
- Camera: BUFFALO BSW500M USB web camera
- USB ID: 0411:02da
- Capture device: device=auto, resolving to /dev/video0 on the target Pi
- Metadata device: /dev/video1, not for capture
- Primary model path: models/yolo_bear_ncnn_model
- Fallback model path: models/yolo_bear.pt
- Recommended resolution: 320x240 on Raspberry Pi 4B
- Recommended FourCC: MJPG first, then YUYV fallback
- Failure behavior: ai_bear_approaching=false
```

If all configured model paths are missing, the system outputs `AI_MODEL_LOAD_ERROR`, sets `ai_model_ok=false`, and remains fail-safe.

Remote monitoring behavior:

```text
Camera AI process
  -> writes CSV: data/logs/camera_ai_log.csv
  -> writes latest annotated frame: data/debug_frames/latest_camera_ai.jpg
Dashboard process
  -> serves browser page: http://<pi-ip>:8080
  -> serves latest image: /camera/latest.jpg
```

During bring-up on the Raspberry Pi, the `.pt` PyTorch fallback hit an
`Illegal instruction` during `YOLO.predict()`. Installing `ncnn` and using
`models/yolo_bear_ncnn_model` fixed the startup path, so the Pi demo should use
the NCNN model as the normal runtime.

If the current Pi `ncnn` runtime (for example the `ncnn==1.0.20260526`
aarch64 build) segfaults inside `extract("out0")`, Camera AI dies immediately
and the dashboard picture freezes on the last frame. You do **not** need to
install PyTorch on the Pi: export `.pt` to ONNX in Colab and drop
`models/yolo_bear.onnx` on the Pi. Camera AI then automatically prefers the
ONNX Runtime inference path (no NCNN, no Pi-side PyTorch/Ultralytics install).
The Raspberry Pi runtime file `raspberry_pi/camera_ai/requirements.txt`
therefore includes `onnxruntime` but excludes PyTorch and Ultralytics. Use
`raspberry_pi/camera_ai/requirements.export.txt` only in Colab or a development
environment for training/export work.

ONNX export flow (run in Colab; Pi only needs the runtime requirements):

```text
1. Open notebooks/export_bear_yolo_onnx.ipynb
2. Upload the repo's best.pt
3. Run all cells to export models/yolo_bear.onnx (imgsz=256, opset 18; opset 12 only if conversion succeeds)
4. Download yolo_bear.onnx and place it at models/yolo_bear.onnx on the Pi
5. Re-run ./scripts/run_demo.sh on the Pi
6. Confirm ai_model_ok=true and that the picture keeps updating
```

When `models/yolo_bear.onnx` exists, `scripts/run_demo.sh` enables inference
by default (`RUN_CAMERA_AI_INFERENCE` becomes 1 automatically). Without ONNX,
the default is the camera-only fail-safe mode (`ai_model_ok=false`, HOLD stays,
picture still keeps updating).
The default `CAMERA_DEVICE=auto` selects the BUFFALO BSW500M Video Capture node;
use `CAMERA_DEVICE=/dev/video0 ./scripts/run_demo.sh` if the demo venue needs a
fixed device path.

Lighten/export a nano `.pt` model for Raspberry Pi 4B:

```bash
python3 raspberry_pi/camera_ai/export_lightweight_yolo.py \
  --source models/yolo_bear.pt \
  --format ncnn \
  --imgsz 256 \
  --overwrite
```

Camera AI run commands:

```bash
python3 -m compileall -q raspberry_pi/camera_ai
python3 raspberry_pi/camera_ai/camera_test.py --device auto
python3 -m raspberry_pi.camera_ai.run_camera_ai --terminal-status --no-jsonl --once
```

Camera debug commands:

```bash
lsusb
ls /dev/video*
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext
fuser -v /dev/video0
```

---

## Folder Responsibilities

| Path | Responsibility |
|---|---|
| `arduino_uno_q/contact_pad_controller/` | Main Arduino Uno controller. Simulated inputs, contact-pad state machine, honey threshold check, RELEASE_ON/OFF output, LED/GPIO, JSON Lines output. |
| `raspberry_pi/logger/` | Raspberry Pi serial logger. Receives Arduino and AI JSON Lines and saves CSV logs. |
| `raspberry_pi/dashboard/` | Simple dashboard for demo and monitoring. Shows the latest contact, AI, and release state. |
| `raspberry_pi/camera_ai/` | Optional Raspberry Pi camera AI perception layer. Tests `/dev/video0`, loads YOLO, estimates bear approach, and publishes AI state. It must not directly command honey release. |
| `docs/` | Design documents, block diagram, state machine, interface specs, and camera AI notes. |
| `data/logs/` | Runtime CSV/JSONL logs. Generated logs are normally kept out of Git except small samples. |
| `examples/` | Small sample input/output files for demos and documentation. |
| `models/` | Local YOLO model weights and exports. Preferred path is `models/yolo_bear_ncnn_model`; `.pt` is fallback only. Commit intentionally only when transferring runtime models. |
| `outputs/` | Generated camera test images and temporary demo outputs. Not committed by default. |
| `scripts/` | Helper scripts for running demos. |
| `tests/` | Python tests for decision logic and camera AI helper behavior. |
| Root files | Project-wide instructions, guardrails, variable list, and multilingual READMEs. |

---

## Development Roadmap

### Phase 1: Simulated Control Logic

```text
[ ] Simulated bear/contact/honey/safety inputs
[ ] RELEASE_ON/OFF decision logic
[ ] Emergency stop and RELEASE_OFF fail-safe
[ ] JSON Lines output
```

### Phase 2: Raspberry Pi Camera Test

```text
[ ] BUFFALO BSW500M connected to Raspberry Pi 4B
[ ] /dev/video0 confirmed as image stream
[ ] /dev/video1 kept unused for capture
[ ] camera_test.py captures one frame
```

### Phase 3: YOLO Model Placement and AI Inference

```text
[ ] Place or export models/yolo_bear_ncnn_model
[ ] Confirm AI_MODEL_LOAD_ERROR disappears
[ ] Run YOLO inference on camera frames
[ ] Publish ai_bear_approaching fail-safe output
```

### Phase 4: AI State Logging and Dashboard Integration

```text
[ ] Log camera AI JSON Lines / CSV
[ ] Show ai_camera_ok and ai_model_ok
[ ] Show ai_bear_detected and ai_bear_approaching
[ ] Display contact and release state together
```

### Phase 5: Resistance / Contact-Pad Integration

```text
[ ] Keep Arduino Uno contact-pad logic
[ ] Add or validate raw_contact_value
[ ] Add contact threshold logic
[ ] Test only with safe dummy objects
```

### Phase 6: PCA9685 / Servo Honey Release Integration

```text
[ ] Connect PCA9685 with external servo power
[ ] Map RELEASE_ON/OFF to safe servo motion
[ ] Add release timeout and cooldown
[ ] Confirm RELEASE_OFF default on reset or error
```

### Phase 7: Full System Demo with Fail-Safe Behavior

```text
[ ] Camera AI detects approach
[ ] Contact/resistance layer confirms paw_contact
[ ] Honey and safety checks pass
[ ] Emergency stop forces RELEASE_OFF
[ ] YOLO-only detection never releases honey
```

---

## How to Explain This to the Team

Use the following explanation.

```text
I will develop the front paw contact pad system as a separate electronic/control module.
Raspberry Pi 4B with a BUFFALO BSW500M camera will be used for YOLO-based bear approach detection, logging, and dashboard support.
Arduino Uno and the contact/resistance layer remain responsible for contact confirmation and fail-safe release logic.
PCA9685 and a servo motor will be used on the honey release mechanism side.
Camera AI is an additional perception layer, not the only safety controller.
```

---

## Current Assumptions

```text
- The honeycomb mechanism can receive a simple RELEASE_ON/OFF signal.
- Raspberry Pi 4B uses /dev/video0 from the BUFFALO BSW500M for image capture.
- /dev/video1 is metadata and must not be used for image capture.
- Physical contact/resistance integration remains separate from camera AI.
- PCA9685 + servo motor + external power supply are used on the actuator side.
- No real animal test will be conducted.
- The project is for hackathon demonstration and concept validation.
```

---

## Definition of Done for MVP v0.1

```text
[ ] Uno can generate simulated inputs
[ ] Uno can decide RELEASE_ON/OFF
[ ] Raspberry Pi can capture from /dev/video0
[ ] Camera AI can publish fail-safe ai_bear_approaching
[ ] RELEASE_ON/OFF is visible through LED or serial output
[ ] Raspberry Pi can receive the state
[ ] Raspberry Pi can save CSV logs
[ ] Safety fallback to RELEASE_OFF is implemented
[ ] YOLO detection alone cannot trigger honey release
[ ] README explains how the system works
[ ] Team can understand the boundary between contact pad and honeycomb mechanism
```

---

## Getting Started (MVP Simulation)

This prototype uses **simulated sensor inputs** and does not require real sensors.

### Arduino Uno

1. Open `arduino_uno_q/contact_pad_controller/contact_pad_controller.ino`.
2. Select **Arduino Uno** in Arduino IDE, then build and upload.
3. Open the serial monitor at **115200 baud**.
4. You should see JSON Lines output.

### Raspberry Pi Logger

1. Install dependencies:
   ```bash
   pip install -r raspberry_pi/logger/requirements.txt
   ```
2. Run the logger:
   ```bash
   python raspberry_pi/logger/serial_logger.py --serial-port /dev/ttyACM0 --baudrate 115200
   ```
3. CSV logs are saved to `data/logs/`.

### Raspberry Pi Camera AI

Run these commands from the repository root on the Raspberry Pi:

```bash
cd ~/Desktop/2026_Hackathon
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/camera_ai/requirements.txt
python -m pip install -r raspberry_pi/dashboard/requirements.txt
```

The Camera AI runtime install is ONNX/NCNN-oriented and intentionally avoids
PyTorch/Ultralytics on the Raspberry Pi.

Normal demo startup, including Camera AI and the remote dashboard:

```bash
./scripts/run_demo.sh
```

Full venue path with live camera inference and Arduino actuator bridge:

```bash
RUN_CAMERA_AI_INFERENCE=1 RUN_ACTUATOR_BRIDGE=1 ./scripts/run_demo.sh
```

The bridge sends Arduino `RELEASE` only from a fresh `RELEASE_ON` safety CSV row;
missing/stale/error data sends or keeps `STOP`.

Open this from another PC, tablet, or phone on the same network, or through Tailscale:

```text
http://<pi-ip>:8080
```

The dashboard shows the latest Camera AI recognition image, AI state, and
contact-pad state. The image is written by Camera AI at:

```text
data/debug_frames/latest_camera_ai.jpg
```

Camera AI only, without the dashboard:

```bash
python -m raspberry_pi.camera_ai.run_camera_ai \
  --device auto \
  --terminal-status \
  --no-jsonl \
  --save-debug-frames
```

One-shot smoke test:

```bash
python -m raspberry_pi.camera_ai.run_camera_ai \
  --device auto \
  --terminal-status \
  --no-jsonl \
  --once \
  --save-debug-frames
```

Camera check:

```bash
python3 raspberry_pi/camera_ai/camera_test.py --device auto
```

### Raspberry Pi Dashboard

Use this only when Camera AI is already running and writing
`data/debug_frames/latest_camera_ai.jpg`:

```bash
python raspberry_pi/dashboard/app.py \
  --log-dir data/logs \
  --camera-log-file data/logs/camera_ai_log.csv \
  --debug-frame-dir data/debug_frames \
  --host 0.0.0.0 \
  --port 8080
```

Open:

```text
http://<pi-ip>:8080
```

To also start the Arduino Uno serial logger during the full demo, run:

```bash
RUN_SERIAL_LOGGER=1 ./scripts/run_demo.sh
```

If port 8080 is already in use:

```bash
DASHBOARD_PORT=18080 ./scripts/run_demo.sh
```

Bring-up check already verified on the target Raspberry Pi path:

```text
- Camera AI loads models/yolo_bear_ncnn_model through NCNN.
- data/debug_frames/latest_camera_ai.jpg is generated.
- Dashboard / returns HTTP 200.
- Dashboard /camera/latest.jpg returns HTTP 200 image/jpeg.
- Stopping the demo leaves no Camera AI or dashboard process running.
```

---

## Demo Mode (Remote Actuator Control)

The dashboard includes a **Demo Mode** panel for safe remote actuator control
during presentations. It allows the operator to manually send commands to the
Arduino-connected servo/mechanism through the Raspberry Pi.

### Architecture

```text
Dashboard (browser)
  ↓ Tailscale / LAN
Raspberry Pi 4B (dashboard backend)
  ↓ USB serial (wired)
Arduino Uno Q
  ↓ GPIO / PCA9685
Servo / Honey release mechanism
```

- The wireless/remote part is **only** Dashboard → Raspberry Pi (via Tailscale or LAN).
- Raspberry Pi → Arduino remains **wired USB serial** for stability.
- The dashboard never talks directly to Arduino.

### Quick Start

Run the full demo (Camera AI + safety control + dashboard):

```bash
./scripts/run_demo.sh
```

Or run the dashboard alone with Demo Mode for hardware testing:

```bash
python raspberry_pi/dashboard/app.py \
  --log-dir data/logs \
  --log-file data/logs/feeding_decision_log.csv \
  --camera-log-file data/logs/camera_ai_log.csv \
  --debug-frame-dir data/debug_frames \
  --demo-serial-port /dev/ttyACM0 \
  --demo-baudrate 115200 \
  --demo-command-log-file data/logs/demo_commands.csv \
  --host 0.0.0.0 \
  --port 8080
```

Open `http://<pi-ip>:8080` from any browser on the same Tailscale network.

### Usage

1. Open the dashboard. The Demo Mode panel shows **DISABLED** by default.
2. Click **Enable Demo Mode** to activate manual control.
3. Use the control buttons:
   - **Release / Open** — sends `RELEASE` to Arduino (requires Demo Mode enabled)
   - **Stop / Close** — sends `STOP` to Arduino (always available)
   - **Test Motion** — sends `TEST` to Arduino (requires Demo Mode enabled)
   - **Emergency Stop** — immediately sends `STOP`, disables Demo Mode, and locks controls
4. The status table shows:
   - Last command sent
   - Command timestamp
   - Serial connection status (`CONNECTED` / `SIMULATION_MODE` / `ERROR`)
   - Result (`SENT` / `SIMULATED` / `BLOCKED` / `ERROR`)
   - Message

### Safety Behavior

- Default state is **STOP / closed**.
- Demo Mode must be manually enabled before `Release` or `Test` commands are accepted.
- `Stop / Close` and `Emergency Stop` are **always** available.
- Emergency Stop immediately sends `STOP` and disables Demo Mode.
- On serial error, the system falls back to **simulation mode** without controlling hardware.

### Simulation Mode (Hardware-Free Rehearsal)

If the Arduino is not connected or the serial port is unavailable, the dashboard
automatically runs in simulation mode:

```bash
# Automatic fallback — just run without Arduino connected
python raspberry_pi/dashboard/app.py --host 0.0.0.0 --port 8080

# Or force simulation mode explicitly
python raspberry_pi/dashboard/app.py --demo-force-simulation --host 0.0.0.0 --port 8080
```

In simulation mode:
- All buttons work normally in the UI.
- Commands are logged to `data/logs/demo_commands.csv`.
- No serial data is sent to hardware.
- Status shows `SIMULATION_MODE`.

### API Endpoints

The dashboard backend exposes these REST endpoints for Demo Mode:

| Endpoint | Method | Description |
|---|---|---|
| `/api/demo-mode` | POST | Enable/disable Demo Mode (`{"enabled": true/false}`) |
| `/api/demo-command` | POST | Send generic command (`{"command": "RELEASE"}`) |
| `/api/demo/release` | POST | Send RELEASE command |
| `/api/demo/stop` | POST | Send STOP command |
| `/api/demo/test` | POST | Send TEST command |
| `/api/demo/emergency-stop` | POST | Send EMERGENCY_STOP command |
| `/api/demo-status` | GET | Get current demo status |

All endpoints return JSON when called with `Accept: application/json` or
`Content-Type: application/json`. From the browser UI, they use HTML form POST
and redirect back to the dashboard.

### Serial Commands

The Raspberry Pi sends these simple string commands over USB serial to Arduino:

| Command | Serial String | Description |
|---|---|---|
| Release / Open | `RELEASE\n` | Activate honey release mechanism |
| Stop / Close | `STOP\n` | Deactivate mechanism (safe default) |
| Test Motion | `TEST\n` | Run a short test motion |
| Emergency Stop | `STOP\n` | Same as STOP, also disables Demo Mode |

### Command Logging

Every demo command is logged to CSV:

```text
data/logs/demo_commands.csv
```

CSV columns: `timestamp`, `command`, `serial_command`, `demo_enabled`,
`serial_status`, `result`, `message`, `emergency_stop`.

### CLI Options

| Option | Default | Description |
|---|---|---|
| `--demo-serial-port` | `/dev/ttyACM0` | Serial port for Arduino connection |
| `--demo-baudrate` | `115200` | Serial baud rate |
| `--demo-command-log-file` | `data/logs/demo_commands.csv` | Path for demo command CSV log |
| `--demo-serial-timeout` | `1.0` | Serial write timeout in seconds |
| `--demo-serial-reset-delay` | `2.0` | Delay after opening serial port |
| `--demo-force-simulation` | (off) | Force simulation mode even if serial port exists |

---

## Data Format Notes

- Arduino Uno sends **JSON Lines**.
- Camera AI also sends **JSON Lines**.
- Raspberry Pi saves **CSV logs**.
- `timestamp` is emitted as **uptime** (`T+<ms>`) until a real-time clock is added.
- See `docs/interface_spec.md` and `docs/camera_ai_interface_spec.md` for the full schema.

---

## One-Sentence Summary

This project uses Raspberry Pi 4B with a BUFFALO BSW500M USB camera for YOLO-based bear approach detection, while preserving the Arduino/contact-pad safety logic so that honey release is allowed only after AI detection, contact confirmation, honey availability, and safety checks are satisfied.
