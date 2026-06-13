from __future__ import annotations

import argparse
import json
import random
import shutil
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_DIR = Path("data/datasets/bear_public_yolo")
DEFAULT_PACKAGE_PATH = Path("data/packages/bear_public_yolo_pi.zip")
DEFAULT_DOWNLOAD_DIR = Path("data/datasets/_downloads/coco2017")
DEFAULT_CLASS_NAME = "Bear"
DEFAULT_YOLO_CLASS_NAME = "bear"
DEFAULT_SPLIT_LIMITS = {
    "train": 160,
    "validation": 40,
}
COCO_ANNOTATIONS_URL = (
    "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
)
COCO_IMAGE_URL_TEMPLATE = "http://images.cocodataset.org/val2017/{file_name}"


def repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else REPO_ROOT / path


def yolo_split_name(open_images_split: str) -> str:
    if open_images_split == "validation":
        return "val"
    return open_images_split


def parse_split_limits(values: list[str] | None) -> dict[str, int]:
    if not values:
        return dict(DEFAULT_SPLIT_LIMITS)

    parsed: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise argparse.ArgumentTypeError(
                f"Invalid split limit {value!r}. Use SPLIT=COUNT, for example train=160."
            )
        split_name, count_text = value.split("=", 1)
        split_name = split_name.strip()
        if split_name not in {"train", "validation", "test"}:
            raise argparse.ArgumentTypeError(
                f"Unsupported split {split_name!r}. Use train, validation, or test."
            )
        try:
            count = int(count_text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"Invalid sample count {count_text!r} for split {split_name!r}."
            ) from exc
        if count <= 0:
            raise argparse.ArgumentTypeError("Sample counts must be positive integers.")
        parsed[split_name] = count
    return parsed


def dataset_yaml_text(dataset_dir: Path, class_name: str) -> str:
    return (
        "path: .\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        "names:\n"
        f"  0: {class_name}\n"
    )


def write_dataset_yaml(dataset_dir: Path, class_name: str) -> Path:
    dataset_yaml_path = dataset_dir / "dataset.yaml"
    dataset_yaml_path.write_text(
        dataset_yaml_text(dataset_dir, class_name),
        encoding="utf-8",
    )
    return dataset_yaml_path


def write_dataset_readme(
    dataset_dir: Path,
    *,
    source_name: str,
    source_class_name: str,
    yolo_class_name: str,
    split_limits: dict[str, int],
) -> Path:
    lines = [
        "# Bear Public YOLO Dataset",
        "",
        "This dataset was prepared for the A1 Bear Honey Buffet camera AI prototype.",
        "It uses public object-detection annotations and converts them into Ultralytics YOLO format.",
        "",
        "Important safety note: this camera AI is only a support signal. It does not replace",
        "the Arduino Uno Q fail-safe contact pad decision logic.",
        "",
        "## Source",
        "",
        f"- Source dataset: {source_name}",
        f"- Source class name: {source_class_name}",
        f"- YOLO class name: {yolo_class_name}",
        "",
        "## Split limits",
        "",
    ]
    for split_name, count in split_limits.items():
        lines.append(f"- {split_name}: up to {count} matching images")
    lines.extend(
        [
            "",
            "## Raspberry Pi usage",
            "",
            "Copy this dataset directory to the repository root on the Raspberry Pi, then train",
            "or export a lightweight model from `models/yolo_bear.pt` as needed.",
            "",
            "Recommended runtime model path:",
            "",
            "```text",
            "models/yolo_bear_ncnn_model",
            "```",
            "",
            "Recommended training command:",
            "",
            "```bash",
            "python raspberry_pi/camera_ai/train_bear_yolo.py \\",
            "  --data data/datasets/bear_public_yolo/dataset.yaml \\",
            "  --imgsz 256 \\",
            "  --epochs 30",
            "```",
            "",
        ]
    )
    readme_path = dataset_dir / "README_PI_DATASET.md"
    readme_path.write_text("\n".join(lines), encoding="utf-8")
    return readme_path


def download_file(url: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path
    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, output_path)
    return output_path


def ensure_coco_val_annotations(download_dir: Path) -> Path:
    zip_path = download_dir / "annotations_trainval2017.zip"
    annotations_path = download_dir / "annotations" / "instances_val2017.json"
    if annotations_path.exists():
        return annotations_path

    download_file(COCO_ANNOTATIONS_URL, zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extract("annotations/instances_val2017.json", download_dir)
    return annotations_path


def coco_bbox_to_yolo(
    bbox_xywh: list[float],
    *,
    image_width: int,
    image_height: int,
) -> tuple[float, float, float, float]:
    x_min, y_min, width, height = [float(value) for value in bbox_xywh]
    x_center = (x_min + width / 2.0) / float(image_width)
    y_center = (y_min + height / 2.0) / float(image_height)
    normalized_width = width / float(image_width)
    normalized_height = height / float(image_height)
    return (
        max(0.0, min(1.0, x_center)),
        max(0.0, min(1.0, y_center)),
        max(0.0, min(1.0, normalized_width)),
        max(0.0, min(1.0, normalized_height)),
    )


def collect_coco_records(
    annotations_path: Path,
    *,
    class_name: str,
    max_images: int,
    validation_fraction: float,
    seed: int,
) -> dict[str, list[dict]]:
    with annotations_path.open("r", encoding="utf-8") as annotations_file:
        coco = json.load(annotations_file)

    category_id = None
    for category in coco.get("categories", []):
        if str(category.get("name", "")).lower() == class_name.lower():
            category_id = int(category["id"])
            break
    if category_id is None:
        raise RuntimeError(f"COCO category was not found: {class_name}")

    images_by_id = {int(image["id"]): image for image in coco.get("images", [])}
    annotations_by_image_id: dict[int, list[dict]] = {}
    for annotation in coco.get("annotations", []):
        if int(annotation.get("category_id", -1)) != category_id:
            continue
        image_id = int(annotation["image_id"])
        annotations_by_image_id.setdefault(image_id, []).append(annotation)

    image_ids = sorted(annotations_by_image_id)
    rng = random.Random(seed)
    rng.shuffle(image_ids)
    selected_image_ids = image_ids[:max_images]

    validation_count = max(1, int(len(selected_image_ids) * validation_fraction))
    validation_ids = set(selected_image_ids[:validation_count])
    records = {"train": [], "val": []}
    for image_id in selected_image_ids:
        image = images_by_id[image_id]
        split_name = "val" if image_id in validation_ids else "train"
        records[split_name].append(
            {
                "image": image,
                "annotations": annotations_by_image_id[image_id],
            }
        )
    return records


def write_coco_yolo_dataset(
    *,
    dataset_dir: Path,
    records_by_split: dict[str, list[dict]],
) -> None:
    for split_name, records in records_by_split.items():
        images_dir = dataset_dir / "images" / split_name
        labels_dir = dataset_dir / "labels" / split_name
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)

        for record in records:
            image = record["image"]
            file_name = str(image["file_name"])
            image_path = images_dir / file_name
            download_file(COCO_IMAGE_URL_TEMPLATE.format(file_name=file_name), image_path)

            label_lines = []
            for annotation in record["annotations"]:
                x_center, y_center, width, height = coco_bbox_to_yolo(
                    annotation["bbox"],
                    image_width=int(image["width"]),
                    image_height=int(image["height"]),
                )
                label_lines.append(
                    f"0 {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
                )
            (labels_dir / f"{Path(file_name).stem}.txt").write_text(
                "\n".join(label_lines) + "\n",
                encoding="utf-8",
            )


def prepare_coco_dataset(
    *,
    dataset_dir: Path,
    download_dir: Path,
    yolo_class_name: str,
    max_images: int,
    validation_fraction: float,
    seed: int,
) -> dict[str, int]:
    annotations_path = ensure_coco_val_annotations(download_dir)
    records_by_split = collect_coco_records(
        annotations_path,
        class_name=yolo_class_name,
        max_images=max_images,
        validation_fraction=validation_fraction,
        seed=seed,
    )
    write_coco_yolo_dataset(dataset_dir=dataset_dir, records_by_split=records_by_split)
    return {split_name: len(records) for split_name, records in records_by_split.items()}


def export_open_images_split(
    *,
    dataset_name: str,
    export_dir: Path,
    open_images_split: str,
    max_samples: int,
    source_class_name: str,
    yolo_class_name: str,
) -> None:
    try:
        import fiftyone as fo
        import fiftyone.zoo as foz
    except ImportError as exc:
        raise RuntimeError(
            "fiftyone is required for Open Images download. Install "
            "raspberry_pi/camera_ai/requirements.dataset.txt on the PC that prepares data."
        ) from exc

    split_dataset_name = f"{dataset_name}-{open_images_split}"
    if split_dataset_name in fo.list_datasets():
        fo.delete_dataset(split_dataset_name)

    dataset = foz.load_zoo_dataset(
        "open-images-v7",
        split=open_images_split,
        label_types=["detections"],
        classes=[source_class_name],
        max_samples=max_samples,
        only_matching=True,
        dataset_name=split_dataset_name,
        overwrite=True,
    )
    dataset.export(
        export_dir=str(export_dir),
        dataset_type=fo.types.YOLOv5Dataset,
        split=yolo_split_name(open_images_split),
        label_field="detections",
        # Keep the source label here so FiftyOne can map Open Images detections.
        # The generated dataset.yaml below normalizes the runtime class name.
        classes=[source_class_name],
        export_media=True,
    )
    fo.delete_dataset(split_dataset_name)


def create_dataset_package(dataset_dir: Path, package_path: Path) -> Path:
    if not dataset_dir.exists():
        raise RuntimeError(f"Dataset directory is missing: {dataset_dir}")

    package_path.parent.mkdir(parents=True, exist_ok=True)
    if package_path.exists():
        package_path.unlink()

    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(dataset_dir.rglob("*")):
            if file_path.is_file():
                if "_downloads" in file_path.relative_to(dataset_dir).parts:
                    continue
                archive.write(file_path, file_path.relative_to(REPO_ROOT))
    return package_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download public bear detections and convert them to YOLO format."
    )
    parser.add_argument(
        "--source",
        choices=("coco2017", "open-images-v7"),
        default="coco2017",
        help="Public dataset source. coco2017 uses only the Python standard library.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_DATASET_DIR),
        help="Output YOLO dataset directory.",
    )
    parser.add_argument(
        "--split-limit",
        action="append",
        default=None,
        metavar="SPLIT=COUNT",
        help="Per-split sample cap. Example: --split-limit train=200 --split-limit validation=50",
    )
    parser.add_argument(
        "--source-class-name",
        default=DEFAULT_CLASS_NAME,
        help="Open Images class name to request.",
    )
    parser.add_argument(
        "--yolo-class-name",
        default=DEFAULT_YOLO_CLASS_NAME,
        help="Class name written to dataset.yaml.",
    )
    parser.add_argument(
        "--dataset-name",
        default="a1-bear-open-images",
        help="Temporary FiftyOne dataset name prefix.",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=80,
        help="Maximum COCO bear images to download when --source coco2017 is used.",
    )
    parser.add_argument(
        "--download-dir",
        default=str(DEFAULT_DOWNLOAD_DIR),
        help="COCO annotation cache directory used when --source coco2017 is selected.",
    )
    parser.add_argument(
        "--validation-fraction",
        type=float,
        default=0.2,
        help="COCO validation fraction when --source coco2017 is used.",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete the existing output dataset directory first.",
    )
    parser.add_argument(
        "--package",
        action="store_true",
        help="Create a Raspberry Pi copy-ready ZIP after export.",
    )
    parser.add_argument(
        "--package-path",
        default=str(DEFAULT_PACKAGE_PATH),
        help="ZIP path used with --package.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    dataset_dir = repo_path(args.output)
    package_path = repo_path(args.package_path)
    split_limits = parse_split_limits(args.split_limit)

    if dataset_dir.exists() and args.overwrite:
        shutil.rmtree(dataset_dir)
    dataset_dir.mkdir(parents=True, exist_ok=True)

    if args.source == "coco2017":
        if args.max_images <= 1:
            raise SystemExit("--max-images must be greater than 1.")
        if not 0.0 < args.validation_fraction < 1.0:
            raise SystemExit("--validation-fraction must be between 0 and 1.")
        split_counts = prepare_coco_dataset(
            dataset_dir=dataset_dir,
            download_dir=repo_path(args.download_dir),
            yolo_class_name=args.yolo_class_name,
            max_images=args.max_images,
            validation_fraction=args.validation_fraction,
            seed=args.seed,
        )
    else:
        for open_images_split, max_samples in split_limits.items():
            export_open_images_split(
                dataset_name=args.dataset_name,
                export_dir=dataset_dir,
                open_images_split=open_images_split,
                max_samples=max_samples,
                source_class_name=args.source_class_name,
                yolo_class_name=args.yolo_class_name,
            )
        split_counts = {
            yolo_split_name(split_name): count for split_name, count in split_limits.items()
        }

    dataset_yaml_path = write_dataset_yaml(dataset_dir, args.yolo_class_name)
    source_class_for_readme = (
        args.yolo_class_name if args.source == "coco2017" else args.source_class_name
    )
    write_dataset_readme(
        dataset_dir,
        source_name=args.source,
        source_class_name=source_class_for_readme,
        yolo_class_name=args.yolo_class_name,
        split_limits=split_counts,
    )

    print(dataset_yaml_path)
    if args.package:
        print(create_dataset_package(dataset_dir, package_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
