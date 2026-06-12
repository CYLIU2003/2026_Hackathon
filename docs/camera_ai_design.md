# Camera AI Design

## Block Diagram

```text
BUFFALO BSW500M USB Camera
  |
  v
Raspberry Pi 4B camera_ai
  |
  +-- camera_test.py: verify capture and save one debug frame
  |
  +-- export_lightweight_yolo.py: export .pt to NCNN/TFLite/ONNX for Pi
  |
  +-- bear_detector.py: lightweight YOLO runtime wrapper, returns detections
  |
  +-- approach_logic.py: confidence, bbox area, consecutive detection
  |
  +-- ai_state_publisher.py: JSON Lines and camera AI CSV log
  |
  v
ai_bear_approaching support signal
```

The camera AI support signal is separate from the Arduino Uno Q contact-pad release controller.

## Responsibility Split

```text
Camera AI:
  - detect possible bear approach
  - prefer Pi-friendly exported YOLO formats such as NCNN
  - publish ai_bear_approaching
  - fail safe to false on errors

Contact pad / release controller:
  - keep paw_contact and raw_contact_value
  - check honey amount, safety, emergency stop
  - decide final RELEASE_ON or RELEASE_OFF
```

## State Meaning

```text
AI_NO_BEAR:
  no configured target class above confidence threshold

AI_BEAR_DETECTED:
  target class was detected, but approach criteria are not yet satisfied

AI_BEAR_APPROACHING:
  target class, confidence, bbox area, and consecutive count criteria are satisfied
```

## Safety Boundary

YOLO detection alone must never trigger honey release.
The final release decision remains fail-safe and must still require contact confirmation, honey availability, system safety, and no emergency stop.

## Raspberry Pi 4B Lightweight Profile

```text
camera capture: 320x240 MJPG at 10 fps
YOLO input_size: 256
primary model: models/yolo_bear_ncnn_model
fallback models:
  - models/yolo_bear_int8.tflite
  - models/yolo_bear.onnx
  - models/yolo_bear.pt
inference interval: 0.75 sec
```
