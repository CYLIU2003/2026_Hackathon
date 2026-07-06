from pathlib import Path

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

    This lets a dropped-in yolo_bear.onnx switch the system to the cv2.dnn
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


def test_default_export_output_paths_match_runtime_fallbacks():
    assert default_output_path("ncnn") == Path("models/yolo_bear_ncnn_model")
    assert default_output_path("onnx") == Path("models/yolo_bear.onnx")
    assert default_output_path("tflite", int8=True) == Path(
        "models/yolo_bear_int8.tflite"
    )
