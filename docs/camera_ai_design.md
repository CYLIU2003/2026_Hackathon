# Camera AI Design

## Block Diagram

```text
BUFFALO BSW500M USB Camera
  - USB ID: 0411:02da
  - /dev/video0: Video Capture
  - /dev/video1: Metadata Capture, not used by OpenCV
  |
  v
Raspberry Pi 4B camera_ai
  |
  +-- camera_capture.py: auto BSW500M video-node selection, OpenCV/V4L2 driver,
  |   /dev/videoN -> OpenCV index fallback, fallback profiles, read retry, reopen
  |
  +-- camera_test.py: verify capture and save one debug frame
  |
  +-- run_camera_ai.py: headless detection loop for logs/dashboard
  |
  +-- web_camera_ai.py: SSH-forwardable live browser viewer
  |
  +-- export_lightweight_yolo.py: export .pt to NCNN/TFLite/ONNX for Pi
  |
  +-- bear_detector.py: lightweight YOLO runtime wrapper, returns detections
  |
  +-- approach_logic.py: confidence-thresholded bear detection
  |
  +-- ai_state_publisher.py: JSON Lines and camera AI CSV log
  |
  v
ai_bear_detected support signal
```

The camera AI support signal is separate from the Arduino Uno Q contact-pad release controller.

## Responsibility Split

```text
Camera AI:
  - detect possible bear presence
  - prefer Pi-friendly exported YOLO formats such as NCNN
  - keep camera driver/reopen logic separate from inference and dashboard code
  - publish ai_bear_detected
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
  target class was detected above confidence threshold
```

## Safety Boundary

YOLO detection alone must never trigger honey release.
The final release decision remains fail-safe and must still require contact confirmation, honey availability, system safety, and no emergency stop.

## Raspberry Pi 4B Lightweight Profile

```text
camera capture: 320x240 MJPG at 5 fps
camera device: auto -> BUFFALO BSW500M Video Capture node, usually /dev/video0
camera recovery: 3 read failures or 3 sec dark frame -> safe reopen
YOLO input_size: 256
primary model: models/yolo_bear_ncnn_model
fallback models:
  - models/yolo_bear_int8.tflite
  - models/yolo_bear.onnx
  - models/yolo_bear.pt
inference interval: about 2.0 sec
remote dashboard JPEG update interval: about 0.2 sec
```

## Runtime And Demo Paths

```text
Headless detection:
  python -m raspberry_pi.camera_ai.run_camera_ai

Dashboard integration:
  run_camera_ai.py writes CSV logs and latest debug frame
  raspberry_pi/dashboard/app.py serves the dashboard

SSH live viewer:
  web_camera_ai.py serves MJPEG + status JSON on 127.0.0.1:8081
  PC opens it through ssh -L 8081:127.0.0.1:8081 <pi-ssh-host>
```

## Training And Model Transfer

```text
prepare_bear_training_data.py
  -> public COCO/Open Images data to YOLO dataset

notebooks/colab_bear_yolo_training.ipynb
  -> optional Colab GPU training

import_colab_artifacts.py
  -> imports a1_camera_ai_colab_artifacts.zip
  -> writes models/yolo_bear.pt
  -> writes models/yolo_bear_ncnn_model

package_pi_camera_ai.py
  -> writes data/packages/camera_ai_raspberry_pi_bundle.zip
```

Selected runtime model files can be committed intentionally for Raspberry Pi
transfer. Raw datasets, logs, debug frames, and Colab byproducts remain ignored.
