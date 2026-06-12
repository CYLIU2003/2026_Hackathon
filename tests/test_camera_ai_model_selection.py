from pathlib import Path

from raspberry_pi.camera_ai.export_lightweight_yolo import default_output_path
from raspberry_pi.camera_ai import run_camera_ai


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


def test_default_export_output_paths_match_runtime_fallbacks():
    assert default_output_path("ncnn") == Path("models/yolo_bear_ncnn_model")
    assert default_output_path("onnx") == Path("models/yolo_bear.onnx")
    assert default_output_path("tflite", int8=True) == Path(
        "models/yolo_bear_int8.tflite"
    )
