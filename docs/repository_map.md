# Repository Map

This file is the quick index for where each kind of work should live.

## Root

| Path | Role |
|---|---|
| `README.md` | Project overview, safety boundary, common bring-up commands |
| `AGENTS.md` | Coding and safety instructions for agents |
| `PROJECT_GUARDRAILS.md` | Project-wide safety constraints |
| `AI_DEVELOPMENT_INSTRUCTIONS.md` | AI/camera development notes |
| `VARIABLES.md` | Shared names and configuration vocabulary |
| `.gitignore` | Keeps generated logs, datasets, caches, and temporary artifacts out of Git |

## Documentation

| Path | Role |
|---|---|
| `docs/feature_overview.md` | Current functional modules and demo entry points |
| `docs/repository_map.md` | File and directory ownership map |
| `docs/block_diagram.md` | System block diagram |
| `docs/state_machine.md` | Contact-pad release state machine |
| `docs/interface_spec.md` | Arduino/contact-pad JSON Lines interface |
| `docs/camera_ai_design.md` | Camera AI design and runtime profile |
| `docs/camera_ai_interface_spec.md` | Camera AI JSON/CSV contract |

## Arduino Uno Q

| Path | Role |
|---|---|
| `arduino_uno_q/contact_pad_controller/contact_pad_controller.ino` | Simulated contact-pad controller and fail-safe release state machine |
| `arduino_uno_q/contact_pad_controller/config.h` | Contact-pad thresholds, timing, pin constants |
| `arduino_uno_q/contact_pad_controller/README.md` | Arduino module run notes |

## Raspberry Pi

| Path | Role |
|---|---|
| `raspberry_pi/camera_ai/` | Camera capture, YOLO inference, AI state publishing, model tooling |
| `raspberry_pi/safety_control/` | Camera + mock contact integration, demo state machine, unified CSV |
| `raspberry_pi/dashboard/` | Browser dashboard for logs and latest camera image |
| `raspberry_pi/logger/` | Serial JSON Lines to CSV logger |
| `raspberry_pi/README.md` | Raspberry Pi module index |

## Camera AI Files

| File | Role |
|---|---|
| `run_camera_ai.py` | Headless camera AI loop for logging/dashboard integration |
| `web_camera_ai.py` | SSH-forwardable live MJPEG viewer with detection boxes |
| `camera_test.py` | One-frame USB camera bring-up test |
| `camera_capture.py` | OpenCV/V4L2 camera open and fallback profiles |
| `bear_detector.py` | Ultralytics YOLO wrapper |
| `approach_logic.py` | Bear approach decision rules |
| `ai_state_publisher.py` | JSON Lines and CSV output |
| `config.camera_ai.yaml` | Camera, model, threshold, and output configuration |
| `prepare_bear_training_data.py` | Public COCO/Open Images to YOLO dataset preparation |
| `train_bear_yolo.py` | Local YOLO training helper |
| `export_lightweight_yolo.py` | `.pt` to NCNN/TFLite/ONNX export helper |
| `import_colab_artifacts.py` | Import Colab ZIP and build final Pi bundle |
| `package_pi_camera_ai.py` | Build Pi copy-ready runtime ZIP |

## Models And Data

| Path | Role |
|---|---|
| `models/yolo_bear_ncnn_model/` | Preferred Pi runtime model |
| `models/yolo_bear.pt` | PyTorch training/export model |
| `data/packages/camera_ai_raspberry_pi_bundle.zip` | Final camera AI bundle for Pi transfer |
| `examples/` | Small sample logs and sample JSON Lines |
| `data/logs/` | Runtime logs, ignored by Git |
| `data/debug_frames/` | Runtime images, ignored by Git |
| `data/datasets/` | Training data and caches, ignored by Git |

## Tests

| Path | Role |
|---|---|
| `tests/test_decision_logic.py` | Contact-pad/release safety logic |
| `tests/test_camera_ai_*.py` | Camera AI helper behavior |
| `tests/test_dashboard.py` | Dashboard route behavior |
| `tests/test_safety_controller.py` | Integrated demo state machine and fail-safe behavior |

## Where New Work Should Go

| New work | Put it here |
|---|---|
| New contact-pad state logic | `arduino_uno_q/contact_pad_controller/` |
| New Raspberry Pi camera behavior | `raspberry_pi/camera_ai/` |
| New presentation-side decision integration | `raspberry_pi/safety_control/` |
| New web display for logs/images | `raspberry_pi/dashboard/` or `web_camera_ai.py` if tied to live camera |
| New interface contracts | `docs/interface_spec.md` or `docs/camera_ai_interface_spec.md` |
| New demo script | `scripts/` |
| New sample data | `examples/` |
