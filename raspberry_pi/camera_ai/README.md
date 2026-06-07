# Camera AI Bear Approach Detection

This prototype adds a Raspberry Pi camera AI module for bear approach detection.
It uses a USB camera and a lightweight YOLO model to publish camera-derived state as JSON Lines.

This module is only an additional perception layer. It does not replace the Arduino Uno Q contact-pad logic, `paw_contact`, `raw_contact_value`, resistance/contact thresholds, or the fail-safe `release_state` decision.

## Hardware

- Raspberry Pi 4B 4GB
- BUFFALO BSW500M USB web camera
- No real sensors are required for this camera AI module
- No real animal testing is part of this prototype

## Setup

Install camera tools on Raspberry Pi:

```bash
sudo apt update
sudo apt install -y v4l-utils
```

Check the camera:

```bash
lsusb
ls /dev/video*
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --all
```

Install Python dependencies:

```bash
pip install -r raspberry_pi/camera_ai/requirements.txt
```

Place a small YOLO model at the path configured in `config.camera_ai.yaml`, for example:

```text
models/yolo_bear.pt
```

Model weights are intentionally ignored by Git.

## Camera Test

Run one-frame capture with a camera index:

```bash
python raspberry_pi/camera_ai/camera_test.py --camera 0
```

Or with a Linux video device path:

```bash
python raspberry_pi/camera_ai/camera_test.py --device /dev/video0
```

The script prints camera properties and saves one debug image under `data/debug_frames/`.

## Run AI Detection

Use the default config:

```bash
python raspberry_pi/camera_ai/run_camera_ai.py --config raspberry_pi/camera_ai/config.camera_ai.yaml
```

Override camera and model:

```bash
python raspberry_pi/camera_ai/run_camera_ai.py --camera 0 --model models/bear_yolo.pt
```

Run one inference cycle:

```bash
python raspberry_pi/camera_ai/run_camera_ai.py --device /dev/video0 --once
```

## Output

The module emits JSON Lines:

```json
{"timestamp":"2026-06-07T12:00:00+09:00","source":"camera_ai","camera_device":"/dev/video0","ai_camera_ok":true,"ai_model_ok":true,"ai_bear_detected":true,"ai_bear_confidence":0.82,"ai_bear_box_area_ratio":0.18,"ai_bear_approaching":true,"event":"AI_BEAR_APPROACHING","inference_time_ms":120.5}
```

If the camera, model, or runtime fails, the output is fail-safe:

```text
ai_bear_approaching=false
```

CSV logs are saved separately from contact-pad logs at `data/logs/camera_ai_log.csv` by default.

## Approach Logic

`ai_bear_approaching` becomes true only when all configured conditions are satisfied:

- target class matches, default `bear`
- confidence is at least `confidence_threshold`
- bounding-box area ratio is at least `approach_area_ratio_threshold`
- the condition is true for `consecutive_required` checks

The camera AI module does not command honey release. A future integration must still require contact confirmation, honey availability, system safety, and no emergency stop before any release request.

## Known Limitations

- A YOLO model is not included in Git.
- Raspberry Pi 4B should use small/nano models and low input sizes such as 320.
- Camera detection can be wrong; it is only a support signal.
- Current integration publishes AI state only and does not modify the Arduino release decision.

