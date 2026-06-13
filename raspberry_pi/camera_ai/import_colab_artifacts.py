from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

try:
    from .package_pi_camera_ai import create_pi_bundle, first_existing_model, repo_path
except ImportError:
    from package_pi_camera_ai import create_pi_bundle, first_existing_model, repo_path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_ZIP = Path("a1_camera_ai_colab_artifacts.zip")
DEFAULT_PI_BUNDLE = Path("data/packages/camera_ai_raspberry_pi_bundle.zip")
EXPECTED_RUNTIME_PATHS = (
    Path("models/yolo_bear_ncnn_model"),
    Path("models/yolo_bear.onnx"),
    Path("models/yolo_bear.pt"),
)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def safe_extract(archive_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target_path = (destination / member.filename).resolve()
            if not is_relative_to(target_path, destination):
                raise RuntimeError(f"Unsafe ZIP member path: {member.filename}")
        archive.extractall(destination)


def runtime_paths_status() -> list[tuple[Path, bool]]:
    return [(path, repo_path(path).exists()) for path in EXPECTED_RUNTIME_PATHS]


def require_runtime_model() -> Path:
    model_path = first_existing_model(EXPECTED_RUNTIME_PATHS)
    if model_path is None:
        checked = ", ".join(str(path) for path, _ in runtime_paths_status())
        raise RuntimeError(f"No runtime model was found. Checked: {checked}")
    return model_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import Colab training artifacts and build the Raspberry Pi camera AI bundle."
    )
    parser.add_argument(
        "--artifact",
        default=str(DEFAULT_ARTIFACT_ZIP),
        help="Path to a1_camera_ai_colab_artifacts.zip downloaded from Colab.",
    )
    parser.add_argument(
        "--bundle-output",
        default=str(DEFAULT_PI_BUNDLE),
        help="Final Raspberry Pi bundle ZIP path.",
    )
    parser.add_argument(
        "--clean-existing-models",
        action="store_true",
        help="Remove existing yolo_bear runtime artifacts before extracting.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    artifact_path = repo_path(args.artifact)
    if not artifact_path.exists():
        raise SystemExit(
            f"Colab artifact ZIP is missing: {artifact_path}\n"
            "Download a1_camera_ai_colab_artifacts.zip from Colab and place it at the repository root, "
            "or pass --artifact."
        )

    if args.clean_existing_models:
        for relative_path in EXPECTED_RUNTIME_PATHS:
            resolved_path = repo_path(relative_path)
            if resolved_path.is_dir():
                shutil.rmtree(resolved_path)
            elif resolved_path.exists():
                resolved_path.unlink()

    safe_extract(artifact_path, REPO_ROOT)
    model_path = require_runtime_model()
    bundle_path = create_pi_bundle(
        package_path=repo_path(args.bundle_output),
        model_path=model_path,
        require_model=True,
        include_dataset=None,
    )

    print(f"runtime_model={model_path}")
    print(f"pi_bundle={bundle_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
