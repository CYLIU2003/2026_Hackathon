from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACKAGE_PATH = Path("data/packages/camera_ai_raspberry_pi_bundle.zip")
DEFAULT_MODEL_CANDIDATES = (
    Path("models/yolo_bear_ncnn_model"),
    Path("models/yolo_bear_int8.tflite"),
    Path("models/yolo_bear.onnx"),
    Path("models/yolo_bear.pt"),
)
CAMERA_AI_FILES = (
    Path("raspberry_pi/camera_ai/__init__.py"),
    Path("raspberry_pi/camera_ai/ai_state_publisher.py"),
    Path("raspberry_pi/camera_ai/approach_logic.py"),
    Path("raspberry_pi/camera_ai/bear_detector.py"),
    Path("raspberry_pi/camera_ai/camera_capture.py"),
    Path("raspberry_pi/camera_ai/camera_test.py"),
    Path("raspberry_pi/camera_ai/config.camera_ai.yaml"),
    Path("raspberry_pi/camera_ai/export_lightweight_yolo.py"),
    Path("raspberry_pi/camera_ai/README.md"),
    Path("raspberry_pi/camera_ai/requirements.txt"),
    Path("raspberry_pi/camera_ai/run_camera_ai.py"),
)


def repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else REPO_ROOT / path


def iter_files(path: Path):
    if path.is_file():
        yield path
        return
    if path.is_dir():
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                yield file_path


def first_existing_model(candidates: tuple[Path, ...] = DEFAULT_MODEL_CANDIDATES) -> Path | None:
    for candidate in candidates:
        resolved = repo_path(candidate)
        if resolved.exists():
            return resolved
    return None


def write_pi_bundle_readme(archive: zipfile.ZipFile, *, model_path: Path | None) -> None:
    model_text = (
        str(model_path.relative_to(REPO_ROOT)).replace("\\", "/")
        if model_path is not None
        else "No model was included. Add models/yolo_bear_ncnn_model or models/yolo_bear.pt."
    )
    readme_text = f"""# Raspberry Pi Camera AI Bundle

This ZIP contains the camera AI runtime files for the A1 Bear Honey Buffet prototype.

Safety boundary: camera AI is only an additional perception signal. Honey release still
requires the Arduino Uno Q contact-pad state machine and fail-safe RELEASE_OFF behavior.

Included model:

```text
{model_text}
```

On the Raspberry Pi:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/camera_ai/requirements.txt
python raspberry_pi/camera_ai/run_camera_ai.py --device /dev/video0 --terminal-status --max-iterations 5
```
"""
    archive.writestr("README_PI_CAMERA_AI_BUNDLE.md", readme_text)


def create_pi_bundle(
    *,
    package_path: Path,
    model_path: Path | None,
    require_model: bool,
    include_dataset: Path | None,
) -> Path:
    if require_model and model_path is None:
        raise RuntimeError(
            "No camera AI model found. Export models/yolo_bear_ncnn_model or train "
            "models/yolo_bear.pt before packaging."
        )

    package_path.parent.mkdir(parents=True, exist_ok=True)
    if package_path.exists():
        package_path.unlink()

    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path in CAMERA_AI_FILES:
            resolved_path = repo_path(relative_path)
            if resolved_path.exists():
                archive.write(resolved_path, relative_path.as_posix())

        if model_path is not None:
            for file_path in iter_files(model_path):
                archive.write(file_path, file_path.relative_to(REPO_ROOT).as_posix())

        if include_dataset is not None:
            for file_path in iter_files(include_dataset):
                archive.write(file_path, file_path.relative_to(REPO_ROOT).as_posix())

        write_pi_bundle_readme(archive, model_path=model_path)

    return package_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a Raspberry Pi copy-ready ZIP for camera AI runtime files."
    )
    parser.add_argument("--output", default=str(DEFAULT_PACKAGE_PATH))
    parser.add_argument(
        "--model",
        default=None,
        help="Model path to include. Default uses the first runtime fallback that exists.",
    )
    parser.add_argument(
        "--require-model",
        action="store_true",
        help="Fail if no model exists yet.",
    )
    parser.add_argument(
        "--include-dataset",
        default=None,
        help="Optional YOLO dataset directory to include in the same ZIP.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    model_path = repo_path(args.model) if args.model else first_existing_model()
    if model_path is not None and not model_path.exists():
        raise SystemExit(f"Model path is missing: {model_path}")

    include_dataset = repo_path(args.include_dataset) if args.include_dataset else None
    if include_dataset is not None and not include_dataset.exists():
        raise SystemExit(f"Dataset path is missing: {include_dataset}")

    try:
        package_path = create_pi_bundle(
            package_path=repo_path(args.output),
            model_path=model_path,
            require_model=args.require_model,
            include_dataset=include_dataset,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(package_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
