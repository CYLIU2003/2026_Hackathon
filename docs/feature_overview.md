# Feature Overview

This project is split into small modules so the camera AI, contact pad logic,
logging, dashboard, and training workflow can evolve independently.

## MVP Safety Flow

```text
Camera AI support signal
  -> ai_bear_approaching

Contact pad controller
  -> paw_contact / raw_contact_value

Safety decision
  -> honey enough
  -> system safe
  -> emergency stop inactive

Output
  -> RELEASE_ON / RELEASE_OFF
```

Camera AI is only a support signal. It must never directly command honey
release.

## Implemented Feature Groups

| Feature | Status | Main files |
|---|---|---|
| Arduino Uno Q simulated contact-pad controller | Implemented | `arduino_uno_q/contact_pad_controller/contact_pad_controller.ino`, `config.h` |
| Release safety state machine | Implemented | `arduino_uno_q/contact_pad_controller/`, `tests/test_decision_logic.py` |
| Raspberry Pi serial CSV logger | Implemented | `raspberry_pi/logger/serial_logger.py` |
| Camera + mock contact safety decision mirror | Implemented | `raspberry_pi/safety_control/safety_controller.py` |
| Raspberry Pi dashboard | Implemented | `raspberry_pi/dashboard/app.py` |
| USB camera smoke test | Implemented | `raspberry_pi/camera_ai/camera_test.py` |
| Camera AI detection loop | Implemented | `raspberry_pi/camera_ai/run_camera_ai.py` |
| Bear detector wrapper | Implemented | `raspberry_pi/camera_ai/bear_detector.py` |
| Bear approach logic | Implemented | `raspberry_pi/camera_ai/approach_logic.py` |
| Camera AI JSON/CSV publisher | Implemented | `raspberry_pi/camera_ai/ai_state_publisher.py` |
| SSH-forwardable camera viewer | Implemented | `raspberry_pi/camera_ai/web_camera_ai.py` |
| Public data preparation | Implemented | `raspberry_pi/camera_ai/prepare_bear_training_data.py` |
| Local YOLO training helper | Implemented | `raspberry_pi/camera_ai/train_bear_yolo.py` |
| Colab GPU training notebook | Implemented | `notebooks/colab_bear_yolo_training.ipynb` |
| Model export and Pi packaging | Implemented | `export_lightweight_yolo.py`, `package_pi_camera_ai.py`, `import_colab_artifacts.py` |

## Demo Entry Points

Use these commands from the repository root on the Raspberry Pi.

Camera AI + mock contact safety decision + CSV + dashboard:

```bash
./scripts/run_demo.sh
```

The dashboard reads `data/logs/feeding_decision_log.csv` and presents the system
as a feeding decision pipeline. The mirror emits `SAFE_TO_FEED`,
`RELEASE/HOLD`, timeout, cooldown, and fail-safe status. It never directly
drives the physical servo.

Example output: `examples/sample_feeding_decision_log.csv`.

Camera AI only:

```bash
python -m raspberry_pi.camera_ai.run_camera_ai \
  --device /dev/video0 \
  --terminal-status \
  --no-jsonl \
  --save-debug-frames
```

SSH-forwardable live viewer:

```bash
python raspberry_pi/camera_ai/web_camera_ai.py \
  --device /dev/video0 \
  --host 127.0.0.1 \
  --port 8081 \
  --terminal-status
```

On the PC:

```powershell
ssh -L 8081:127.0.0.1:8081 <pi-ssh-host>
```

Open:

```text
http://127.0.0.1:8081
```

## Runtime Artifacts

| Artifact | Purpose | Git policy |
|---|---|---|
| `models/yolo_bear_ncnn_model/` | Preferred Raspberry Pi model runtime | Commit intentionally for Pi transfer |
| `models/yolo_bear.pt` | Training/export source and fallback | Commit intentionally for Pi transfer |
| `data/packages/camera_ai_raspberry_pi_bundle.zip` | Copy-ready Pi camera AI bundle | Commit only when intentionally updating Pi bundle |
| `data/logs/` | Runtime logs | Ignored |
| `data/debug_frames/` | Runtime camera frames | Ignored |
| `data/datasets/` | Training datasets and COCO cache | Ignored |
| `a1_camera_ai_colab_artifacts.zip` | Raw Colab download | Ignored after import |
