from pathlib import Path

import numpy as np
import pytest

from raspberry_pi.camera_ai.export_lightweight_yolo import default_output_path
from raspberry_pi.camera_ai import run_camera_ai
from raspberry_pi.camera_ai.bear_detector import YoloBearDetector


def test_resolve_model_path_prefers_existing_lightweight_model(tmp_path, monkeypatch):
    monkeypatch.setattr(run_camera_ai, "REPO_ROOT", tmp_path)
    lightweight_model_dir = tmp_path / "models" / "yolo_bear_ncnn_model"
    fallback_model = tmp_path / "models" / "yolo_bear.pt"
    lightweight_model_dir.mkdir(parents=True)
    fallback_model.write_text("placeholder", encoding="utf-8")

    resolved = run_camera_ai.resolve_model_path(
        {
            "model_path": "models/yolo_bear_ncnn_model",
            "fallback_model_paths": ["models/yolo_bear.pt"],
        }
    )

    assert resolved == lightweight_model_dir


def test_resolve_model_path_uses_fallback_when_lightweight_missing(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(run_camera_ai, "REPO_ROOT", tmp_path)
    fallback_model = tmp_path / "models" / "yolo_bear.pt"
    fallback_model.parent.mkdir(parents=True)
    fallback_model.write_text("placeholder", encoding="utf-8")

    resolved = run_camera_ai.resolve_model_path(
        {
            "model_path": "models/yolo_bear_ncnn_model",
            "fallback_model_paths": ["models/yolo_bear.pt"],
        }
    )

    assert resolved == fallback_model


def test_resolve_model_path_returns_primary_for_clear_load_error(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(run_camera_ai, "REPO_ROOT", tmp_path)

    resolved = run_camera_ai.resolve_model_path(
        {
            "model_path": "models/yolo_bear_ncnn_model",
            "fallback_model_paths": ["models/yolo_bear.pt"],
        }
    )

    assert resolved == Path(tmp_path / "models" / "yolo_bear_ncnn_model")


def test_resolve_model_path_respects_cli_override(tmp_path, monkeypatch):
    monkeypatch.setattr(run_camera_ai, "REPO_ROOT", tmp_path)

    resolved = run_camera_ai.resolve_model_path(
        {"model_path": "models/yolo_bear_ncnn_model"},
        model_override="models/custom_bear.pt",
    )

    assert resolved == Path(tmp_path / "models" / "custom_bear.pt")


def test_resolve_model_candidates_keeps_existing_runtime_fallback_order(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(run_camera_ai, "REPO_ROOT", tmp_path)
    lightweight_model_dir = tmp_path / "models" / "yolo_bear_ncnn_model"
    fallback_model = tmp_path / "models" / "yolo_bear.pt"
    lightweight_model_dir.mkdir(parents=True)
    fallback_model.write_text("placeholder", encoding="utf-8")

    resolved = run_camera_ai.resolve_model_candidates(
        {
            "model_path": "models/yolo_bear_ncnn_model",
            "fallback_model_paths": ["models/yolo_bear.pt"],
        }
    )

    assert resolved == [lightweight_model_dir, fallback_model]


def test_resolve_model_candidates_prefers_onnx_over_ncnn(tmp_path, monkeypatch):
    """When both NCNN dir and ONNX file exist, ONNX is preferred.

    This lets a dropped-in yolo_bear.onnx switch the system to the ONNX Runtime
    ONNX backend automatically on platforms where the NCNN runtime segfaults.
    """
    monkeypatch.setattr(run_camera_ai, "REPO_ROOT", tmp_path)
    ncnn_model_dir = tmp_path / "models" / "yolo_bear_ncnn_model"
    onnx_model = tmp_path / "models" / "yolo_bear.onnx"
    ncnn_model_dir.mkdir(parents=True)
    (ncnn_model_dir / "model.ncnn.param").write_text("placeholder", encoding="utf-8")
    onnx_model.write_text("placeholder", encoding="utf-8")

    resolved = run_camera_ai.resolve_model_candidates(
        {
            "model_path": "models/yolo_bear_ncnn_model",
            "fallback_model_paths": ["models/yolo_bear.onnx"],
        }
    )

    assert resolved[0] == onnx_model
    assert ncnn_model_dir in resolved


def test_load_detector_from_candidates_falls_back_after_runtime_load_error(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(run_camera_ai, "REPO_ROOT", tmp_path)
    lightweight_model_dir = tmp_path / "models" / "yolo_bear_ncnn_model"
    fallback_model = tmp_path / "models" / "yolo_bear.pt"
    lightweight_model_dir.mkdir(parents=True)
    fallback_model.write_text("placeholder", encoding="utf-8")
    attempted_paths = []

    class FakeDetector:
        def __init__(self, model_path, **_kwargs):
            attempted_paths.append(Path(model_path))
            if Path(model_path) == lightweight_model_dir:
                raise RuntimeError("ncnn runtime missing")

    monkeypatch.setattr(run_camera_ai, "YoloBearDetector", FakeDetector)

    detector, resolved_model_path = run_camera_ai.load_detector_from_candidates(
        {
            "model_path": "models/yolo_bear_ncnn_model",
            "fallback_model_paths": ["models/yolo_bear.pt"],
        }
    )

    assert isinstance(detector, FakeDetector)
    assert resolved_model_path == fallback_model
    assert attempted_paths == [lightweight_model_dir, fallback_model]


def test_ncnn_model_without_runtime_fails_before_ultralytics_load(
    tmp_path, monkeypatch
):
    lightweight_model_dir = tmp_path / "models" / "yolo_bear_ncnn_model"
    lightweight_model_dir.mkdir(parents=True)
    (lightweight_model_dir / "model.ncnn.param").write_text(
        "placeholder", encoding="utf-8"
    )

    detector = YoloBearDetector.__new__(YoloBearDetector)
    detector.model_path = str(lightweight_model_dir)
    monkeypatch.setattr(
        "raspberry_pi.camera_ai.bear_detector.importlib.util.find_spec",
        lambda _name: None,
    )

    with pytest.raises(RuntimeError, match="NCNN runtime is not installed"):
        detector._check_runtime_dependency()


def test_onnx_model_without_runtime_fails_with_onnxruntime_guidance(
    tmp_path, monkeypatch
):
    onnx_model = tmp_path / "models" / "yolo_bear.onnx"
    onnx_model.parent.mkdir(parents=True)
    onnx_model.write_text("placeholder", encoding="utf-8")

    detector = YoloBearDetector.__new__(YoloBearDetector)
    detector.model_path = str(onnx_model)

    def fake_find_spec(module_name):
        if module_name == "onnxruntime":
            return None
        return object()

    monkeypatch.setattr(
        "raspberry_pi.camera_ai.bear_detector.importlib.util.find_spec",
        fake_find_spec,
    )

    with pytest.raises(RuntimeError, match="ONNX Runtime is not installed"):
        detector._check_runtime_dependency()


def test_onnxruntime_detection_uses_exported_images_tensor_shape():
    import cv2

    class FakeOnnxSession:
        def __init__(self):
            self.feed = None

        def run(self, output_names, feed):
            self.feed = feed
            out = np.zeros((1, 5, 1344), dtype=np.float32)
            out[0, :, 0] = [128.0, 128.0, 64.0, 64.0, 0.9]
            return [out]

    fake_session = FakeOnnxSession()
    detector = YoloBearDetector.__new__(YoloBearDetector)
    detector._cv2 = cv2
    detector._onnx_session = fake_session
    detector._onnx_input_name = "images"
    detector._onnx_output_names = ["output0"]
    detector.input_size = 256
    detector.confidence_floor = 0.5
    detector.class_ids = ()
    detector._class_names = {0: "bear"}

    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    detections = detector._detect_onnx(frame)

    feed_tensor = fake_session.feed["images"]
    assert feed_tensor.shape == (1, 3, 256, 256)
    assert feed_tensor.dtype == np.float32
    assert detections == [
        {
            "class_name": "bear",
            "confidence": pytest.approx(0.9),
            "bbox_xyxy": [120.0, 90.0, 200.0, 150.0],
            "box_area_ratio": pytest.approx(0.0625),
        }
    ]


def test_default_export_output_paths_match_runtime_fallbacks():
    assert default_output_path("ncnn") == Path("models/yolo_bear_ncnn_model")
    assert default_output_path("onnx") == Path("models/yolo_bear.onnx")
    assert default_output_path("tflite", int8=True) == Path(
        "models/yolo_bear_int8.tflite"
    )
