from __future__ import annotations

from pathlib import Path
from typing import Any


class YoloBearDetector:
    """Small YOLO wrapper that returns plain detection dictionaries."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        input_size: int = 320,
        confidence_floor: float = 0.01,
    ):
        self.model_path = str(model_path)
        self.input_size = int(input_size)
        self.confidence_floor = float(confidence_floor)

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "ultralytics is not installed. Install raspberry_pi/camera_ai/requirements.txt."
            ) from exc

        try:
            self.model = YOLO(self.model_path)
        except Exception as exc:
            raise RuntimeError(f"failed to load YOLO model: {self.model_path}") from exc

    def detect(self, frame: Any) -> list[dict]:
        frame_height, frame_width = frame.shape[:2]
        frame_area = max(1, int(frame_width) * int(frame_height))
        results = self.model.predict(
            frame,
            imgsz=self.input_size,
            conf=self.confidence_floor,
            verbose=False,
        )

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

