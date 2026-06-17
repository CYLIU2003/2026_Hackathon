from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


class YoloBearDetector:
    """Small YOLO wrapper that returns plain detection dictionaries."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        input_size: int = 256,
        confidence_floor: float = 0.05,
        device: str | None = "cpu",
        class_ids: list[int] | tuple[int, ...] | None = None,
        enable_model_fusion: bool = True,
    ):
        self.model_path = str(model_path)
        self.input_size = int(input_size)
        self.confidence_floor = float(confidence_floor)
        self.device = device
        self.class_ids = tuple(int(class_id) for class_id in (class_ids or ()))
        if self.input_size <= 0:
            raise RuntimeError("YOLO input_size must be a positive integer.")
        if not Path(self.model_path).exists():
            raise RuntimeError(
                f"YOLO model file is missing: {self.model_path}. "
                "Place an exported lightweight model at models/yolo_bear_ncnn_model "
                "or a fallback prototype model at models/yolo_bear.pt."
            )
        self._check_runtime_dependency()

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "ultralytics is not installed. Install raspberry_pi/camera_ai/requirements.txt."
            ) from exc

        try:
            self.model = YOLO(self.model_path, task="detect")
        except Exception as exc:
            raise RuntimeError(f"failed to load YOLO model: {self.model_path}") from exc
        self._ensure_backend_ready()
        if enable_model_fusion:
            self._try_fuse_model()

    def detect(self, frame: Any) -> list[dict]:
        frame_height, frame_width = frame.shape[:2]
        frame_area = max(1, int(frame_width) * int(frame_height))
        predict_kwargs = {
            "imgsz": self.input_size,
            "conf": self.confidence_floor,
            "verbose": False,
        }
        if self.device:
            predict_kwargs["device"] = self.device
        if self.class_ids:
            predict_kwargs["classes"] = list(self.class_ids)
        results = self.model.predict(frame, **predict_kwargs)

        detections: list[dict] = []
        for result in results:
            names = result.names
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            for box in boxes:
                xyxy = [float(value) for value in box.xyxy[0].cpu().tolist()]
                confidence = float(box.conf[0].cpu().item())
                class_index = int(box.cls[0].cpu().item())
                class_name = str(names.get(class_index, class_index)).lower()
                box_area_ratio = self._box_area_ratio(xyxy, frame_area)
                detections.append(
                    {
                        "class_name": class_name,
                        "confidence": confidence,
                        "bbox_xyxy": xyxy,
                        "box_area_ratio": box_area_ratio,
                    }
                )

        return sorted(
            detections,
            key=lambda detection: float(detection["confidence"]),
            reverse=True,
        )

    @staticmethod
    def _box_area_ratio(bbox_xyxy: list[float], frame_area: int) -> float:
        x1, y1, x2, y2 = bbox_xyxy
        width = max(0.0, x2 - x1)
        height = max(0.0, y2 - y1)
        return min(1.0, (width * height) / float(frame_area))

    def _try_fuse_model(self) -> None:
        fuse = getattr(self.model, "fuse", None)
        if not callable(fuse):
            return
        try:
            fuse()
        except Exception:
            return

    def _ensure_backend_ready(self) -> None:
        try:
            _ = self.model.names
        except Exception as exc:
            raise RuntimeError(
                f"failed to initialize YOLO runtime backend: {self.model_path}"
            ) from exc

    def _check_runtime_dependency(self) -> None:
        model_path = Path(self.model_path)
        is_ncnn_export = model_path.is_dir() and any(model_path.glob("*.ncnn.param"))
        if is_ncnn_export and importlib.util.find_spec("ncnn") is None:
            raise RuntimeError(
                "NCNN runtime is not installed. Install ncnn on the Raspberry Pi "
                "or use fallback PyTorch weights such as models/yolo_bear.pt."
            )
