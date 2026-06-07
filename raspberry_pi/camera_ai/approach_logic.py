from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Iterable, Optional


@dataclass(frozen=True)
class ApproachDetectionConfig:
    target_classes: tuple[str, ...] = ("bear",)
    confidence_threshold: float = 0.50
    approach_area_ratio_threshold: float = 0.12
    consecutive_required: int = 3
    max_detection_age_sec: float = 2.0

    @classmethod
    def from_mapping(cls, values: dict) -> "ApproachDetectionConfig":
        return cls(
            target_classes=tuple(
                str(class_name).lower()
                for class_name in values.get("target_classes", ["bear"])
            ),
            confidence_threshold=float(values.get("confidence_threshold", 0.50)),
            approach_area_ratio_threshold=float(
                values.get("approach_area_ratio_threshold", 0.12)
            ),
            consecutive_required=max(1, int(values.get("consecutive_required", 3))),
            max_detection_age_sec=float(values.get("max_detection_age_sec", 2.0)),
        )


@dataclass(frozen=True)
class ApproachDecision:
    ai_bear_detected: bool
    ai_bear_confidence: Optional[float]
    ai_bear_box_area_ratio: Optional[float]
    ai_bear_approaching: bool
    consecutive_count: int
    event: str


class ApproachLogic:
    """Convert YOLO object detections into a fail-safe approach decision."""

    def __init__(self, config: ApproachDetectionConfig):
        self.config = config
        self._consecutive_count = 0
        self._last_valid_detection_time: Optional[float] = None

    def update(
        self,
        detections: Iterable[dict],
        now_monotonic: Optional[float] = None,
    ) -> ApproachDecision:
        now_monotonic = monotonic() if now_monotonic is None else now_monotonic
        best_target_detection = self._best_target_detection(detections)
        best_confident_detection = self._best_confident_detection(best_target_detection)
        best_valid_detection = self._best_valid_detection(best_confident_detection)

        if best_valid_detection is None:
            self._consecutive_count = 0
            self._last_valid_detection_time = None
        else:
            if (
                self._last_valid_detection_time is None
                or now_monotonic - self._last_valid_detection_time
                > self.config.max_detection_age_sec
            ):
                self._consecutive_count = 1
            else:
                self._consecutive_count += 1
            self._last_valid_detection_time = now_monotonic

        ai_bear_approaching = (
            self._consecutive_count >= self.config.consecutive_required
        )
        ai_bear_detected = best_confident_detection is not None

        confidence = (
            float(best_confident_detection["confidence"])
            if best_confident_detection is not None
            else None
        )
        area_ratio = (
            float(best_confident_detection["box_area_ratio"])
            if best_confident_detection is not None
            else None
        )

        if ai_bear_approaching:
            event = "AI_BEAR_APPROACHING"
        elif ai_bear_detected:
            event = "AI_BEAR_DETECTED"
        else:
            event = "AI_NO_BEAR"

        return ApproachDecision(
            ai_bear_detected=ai_bear_detected,
            ai_bear_confidence=confidence,
            ai_bear_box_area_ratio=area_ratio,
            ai_bear_approaching=ai_bear_approaching,
            consecutive_count=self._consecutive_count,
            event=event,
        )

    def reset(self) -> None:
        self._consecutive_count = 0
        self._last_valid_detection_time = None

    def _best_target_detection(self, detections: Iterable[dict]) -> Optional[dict]:
        target_classes = {class_name.lower() for class_name in self.config.target_classes}
        matching_detections = [
            detection
            for detection in detections
            if str(detection.get("class_name", "")).lower() in target_classes
        ]
        return max(
            matching_detections,
            key=lambda detection: float(detection.get("confidence", 0.0)),
            default=None,
        )

    def _best_confident_detection(
        self, detection: Optional[dict]
    ) -> Optional[dict]:
        if detection is None:
            return None
        if float(detection.get("confidence", 0.0)) < self.config.confidence_threshold:
            return None
        return detection

    def _best_valid_detection(self, detection: Optional[dict]) -> Optional[dict]:
        if detection is None:
            return None
        if (
            float(detection.get("box_area_ratio", 0.0))
            < self.config.approach_area_ratio_threshold
        ):
            return None
        return detection

