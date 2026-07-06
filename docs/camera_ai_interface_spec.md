# Camera AI Interface Spec

## Purpose

The camera AI module publishes a camera-derived bear approach signal from Raspberry Pi 4B.
It is an additional perception layer and does not replace the contact pad, resistance/contact measurement, or Arduino Uno Q fail-safe release decision.

## JSON Lines Output

One JSON object is printed per line.

Required fields:

```json
{
  "timestamp": "ISO-8601 string",
  "source": "camera_ai",
  "camera_device": "/dev/video0",
  "ai_camera_ok": true,
  "ai_model_ok": true,
  "ai_bear_detected": true,
  "ai_bear_confidence": 0.82,
  "ai_bear_box_area_ratio": 0.18,
  "ai_bear_approaching": true,
  "event": "AI_BEAR_APPROACHING",
  "inference_time_ms": 120.5
}
```

Events:

```text
AI_NO_BEAR
AI_BEAR_DETECTED
AI_BEAR_APPROACHING
AI_CAMERA_OPEN_ERROR
AI_CAMERA_FRAME_ERROR
AI_MODEL_LOAD_ERROR
AI_RUNTIME_ERROR
```

## CSV Log

Default path:

```text
data/logs/camera_ai_log.csv
```

Columns:

```csv
timestamp,source,camera_device,ai_camera_ok,ai_model_ok,ai_bear_detected,ai_bear_confidence,ai_bear_box_area_ratio,ai_bear_approaching,event,inference_time_ms
```

Camera AI logs are separate from contact-pad logs.

## Fail-Safe Behavior

On camera failure, model failure, low confidence, timeout, or exception:

```text
ai_bear_approaching=false
```

This module must not directly set `release_state` to `RELEASE_ON`.

## Model Runtime Contract

The Pi 4B 4GB runtime should prefer exported lightweight models over raw
PyTorch weights. If `models/yolo_bear.onnx` exists, the loader prefers it over
NCNN to avoid native-runtime crashes seen on some Pi images:

```text
preferred: models/yolo_bear.onnx or models/yolo_bear_ncnn_model
fallbacks:
  - models/yolo_bear_int8.tflite
  - models/yolo_bear.pt
```

If no configured model path exists or the model cannot be loaded, emit
`AI_MODEL_LOAD_ERROR` and keep `ai_bear_approaching=false`.

The runtime tries all existing configured model paths in order. This allows a
transferred training result such as `models/yolo_bear.pt` to work even when the
preferred `models/yolo_bear_ncnn_model` export is present but the NCNN Python
runtime is not installed yet.

For Raspberry Pi 4B operation, install
`raspberry_pi/camera_ai/requirements.txt` and use `models/yolo_bear.onnx` or
`models/yolo_bear_ncnn_model` as the normal runtime path. ONNX models are run
with ONNX Runtime, so opset 18 exports are acceptable. This runtime requirements
file intentionally excludes PyTorch and Ultralytics. The PyTorch `.pt` fallback
is intended mainly for development and transfer convenience and requires
`raspberry_pi/camera_ai/requirements.export.txt` in a Colab or development
environment.

## Future Integration

Correct future integration style:

```python
release_allowed = (
    ai_bear_approaching
    and paw_contact
    and honey_amount_percent >= honey_min_threshold_percent
    and system_safe
    and not emergency_stop
)
```

The fields `paw_contact`, `raw_contact_value`, contact thresholds, `honey_amount_percent`, `system_safe`, `emergency_stop`, and `release_state` remain part of the existing contact-pad/release interface.
