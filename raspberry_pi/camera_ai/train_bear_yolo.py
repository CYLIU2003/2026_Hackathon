from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_YAML = Path("data/datasets/bear_public_yolo/dataset.yaml")
DEFAULT_OUTPUT_MODEL = Path("models/yolo_bear.pt")


def repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else REPO_ROOT / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train a lightweight YOLO bear detector for the Raspberry Pi camera AI."
    )
    parser.add_argument(
        "--data",
        default=str(DEFAULT_DATASET_YAML),
        help="YOLO dataset.yaml path.",
    )
    parser.add_argument(
        "--base-model",
        default="yolov8n.pt",
        help="Ultralytics base model. yolov8n.pt is the default lightweight prototype.",
    )
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--imgsz", type=int, default=256)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--project", default="runs/camera_ai_train")
    parser.add_argument("--name", default="bear_yolo")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_MODEL),
        help="Final trained PyTorch model path used by export_lightweight_yolo.py.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow Ultralytics to overwrite an existing training run directory.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    dataset_yaml_path = repo_path(args.data)
    output_model_path = repo_path(args.output)

    if not dataset_yaml_path.exists():
        raise SystemExit(
            f"Dataset YAML is missing: {dataset_yaml_path}\n"
            "Run prepare_bear_training_data.py first."
        )
    if args.epochs <= 0:
        raise SystemExit("--epochs must be a positive integer.")
    if args.imgsz <= 0:
        raise SystemExit("--imgsz must be a positive integer.")

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "ultralytics is not installed. Install raspberry_pi/camera_ai/requirements.txt."
        ) from exc

    model = YOLO(args.base_model)
    results = model.train(
        data=str(dataset_yaml_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=str(repo_path(args.project)),
        name=args.name,
        exist_ok=args.overwrite,
    )

    save_dir = Path(getattr(results, "save_dir", repo_path(args.project) / args.name))
    best_model_path = save_dir / "weights" / "best.pt"
    if not best_model_path.exists():
        raise SystemExit(f"Training finished, but best.pt was not found: {best_model_path}")

    output_model_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_model_path, output_model_path)
    print(output_model_path)
    print(
        "Next export command:\n"
        "python raspberry_pi/camera_ai/export_lightweight_yolo.py "
        f"--source {output_model_path.relative_to(REPO_ROOT)} "
        "--format ncnn --imgsz 256 --overwrite"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
