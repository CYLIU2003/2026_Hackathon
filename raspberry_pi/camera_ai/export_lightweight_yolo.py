from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else REPO_ROOT / path


def default_output_path(export_format: str, *, int8: bool = False) -> Path:
    if export_format == "ncnn":
        return Path("models/yolo_bear_ncnn_model")
    if export_format == "tflite" and int8:
        return Path("models/yolo_bear_int8.tflite")
    if export_format == "tflite":
        return Path("models/yolo_bear.tflite")
    return Path("models/yolo_bear.onnx")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a YOLO bear detector to a Raspberry Pi friendly format."
    )
    parser.add_argument(
        "--source",
        default="models/yolo_bear.pt",
        help="Source PyTorch YOLO model. Use a nano/small model for Raspberry Pi 4B.",
    )
    parser.add_argument(
        "--format",
        choices=("ncnn", "tflite", "onnx"),
        default="ncnn",
        help="Export format. NCNN is the default CPU-friendly target for Raspberry Pi.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=256,
        help="Export input size. 256 is the default lightweight Pi profile.",
    )
    parser.add_argument(
        "--int8",
        action="store_true",
        help="Request INT8 quantization when supported by the selected export format.",
    )
    parser.add_argument(
        "--half",
        action="store_true",
        help="Request FP16 export when supported. Do not use this for Pi CPU-only runs.",
    )
    parser.add_argument(
        "--data",
        default=None,
        help="Dataset yaml for calibration when INT8 export requires representative data.",
    )
    parser.add_argument(
        "--nms",
        action="store_true",
        help="Include NMS in the exported model when the backend supports it.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Final exported model path. Default matches the runtime fallback order.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing output file or directory.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_path = repo_path(args.source)
    if not source_path.exists():
        raise SystemExit(
            f"Source model is missing: {source_path}\n"
            "Place a trained or COCO-pretrained nano model at models/yolo_bear.pt first."
        )
    if args.imgsz <= 0:
        raise SystemExit("--imgsz must be a positive integer.")

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "ultralytics is not installed. Install raspberry_pi/camera_ai/requirements.txt."
        ) from exc

    export_kwargs = {
        "format": args.format,
        "imgsz": args.imgsz,
        "int8": args.int8,
        "half": args.half,
        "nms": args.nms,
    }
    if args.data:
        export_kwargs["data"] = str(repo_path(args.data))

    exported_path = Path(YOLO(str(source_path)).export(**export_kwargs))
    output_path = repo_path(args.output or default_output_path(args.format, int8=args.int8))
    if output_path.exists():
        if not args.overwrite:
            raise SystemExit(
                f"Output already exists: {output_path}\n"
                "Use --overwrite to replace it."
            )
        if output_path.is_dir():
            shutil.rmtree(output_path)
        else:
            output_path.unlink()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if exported_path.resolve() != output_path.resolve():
        shutil.move(str(exported_path), str(output_path))
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
