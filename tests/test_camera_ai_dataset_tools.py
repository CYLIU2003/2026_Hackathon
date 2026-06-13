from pathlib import Path

from raspberry_pi.camera_ai import package_pi_camera_ai, prepare_bear_training_data


def test_yolo_split_name_maps_open_images_validation_to_val():
    assert prepare_bear_training_data.yolo_split_name("validation") == "val"
    assert prepare_bear_training_data.yolo_split_name("train") == "train"


def test_dataset_yaml_text_stays_portable_for_raspberry_pi(tmp_path):
    dataset_yaml = prepare_bear_training_data.dataset_yaml_text(tmp_path, "bear")

    assert "path: ." in dataset_yaml
    assert "train: images/train" in dataset_yaml
    assert "val: images/val" in dataset_yaml
    assert "0: bear" in dataset_yaml


def test_parse_split_limits_defaults_to_train_and_validation():
    assert prepare_bear_training_data.parse_split_limits(None) == {
        "train": 160,
        "validation": 40,
    }


def test_parse_split_limits_accepts_cli_values():
    assert prepare_bear_training_data.parse_split_limits(["train=12", "test=3"]) == {
        "train": 12,
        "test": 3,
    }


def test_coco_bbox_to_yolo_normalizes_xywh_box():
    assert prepare_bear_training_data.coco_bbox_to_yolo(
        [10, 20, 30, 40],
        image_width=100,
        image_height=200,
    ) == (0.25, 0.2, 0.3, 0.2)


def test_first_existing_model_prefers_lightweight_runtime(tmp_path, monkeypatch):
    lightweight_model_dir = tmp_path / "models" / "yolo_bear_ncnn_model"
    fallback_model = tmp_path / "models" / "yolo_bear.pt"
    lightweight_model_dir.mkdir(parents=True)
    fallback_model.write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(package_pi_camera_ai, "REPO_ROOT", tmp_path)

    assert package_pi_camera_ai.first_existing_model() == lightweight_model_dir


def test_create_pi_bundle_includes_model_and_readme(tmp_path, monkeypatch):
    monkeypatch.setattr(package_pi_camera_ai, "REPO_ROOT", tmp_path)
    model_path = tmp_path / "models" / "yolo_bear.pt"
    model_path.parent.mkdir(parents=True)
    model_path.write_text("placeholder", encoding="utf-8")

    package_path = package_pi_camera_ai.create_pi_bundle(
        package_path=tmp_path / "bundle.zip",
        model_path=model_path,
        require_model=True,
        include_dataset=None,
    )

    assert package_path.exists()

    import zipfile

    with zipfile.ZipFile(package_path) as archive:
        names = set(archive.namelist())

    assert "models/yolo_bear.pt" in names
    assert "README_PI_CAMERA_AI_BUNDLE.md" in names
