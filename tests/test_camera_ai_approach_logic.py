from pathlib import Path
import sys

CAMERA_AI_DIR = Path(__file__).resolve().parents[1] / "raspberry_pi" / "camera_ai"
sys.path.insert(0, str(CAMERA_AI_DIR))

from approach_logic import ApproachDetectionConfig, ApproachLogic


def bear_detection(confidence=0.82, box_area_ratio=0.18):
    return {
        "class_name": "bear",
        "confidence": confidence,
        "bbox_xyxy": [120, 80, 300, 260],
        "box_area_ratio": box_area_ratio,
    }


def test_no_bear_is_not_detected():
    logic = ApproachLogic(ApproachDetectionConfig())
    decision = logic.update([], now_monotonic=1.0)

    assert decision.ai_bear_detected is False
    assert decision.event == "AI_NO_BEAR"


def test_low_confidence_is_fail_safe_false():
    logic = ApproachLogic(ApproachDetectionConfig(confidence_threshold=0.5))
    decision = logic.update([bear_detection(confidence=0.49)], now_monotonic=1.0)

    assert decision.ai_bear_detected is False


def test_small_bbox_detected_is_enough_for_demo():
    logic = ApproachLogic(
        ApproachDetectionConfig(
            confidence_threshold=0.5,
            approach_area_ratio_threshold=0.12,
        )
    )
    decision = logic.update([bear_detection(box_area_ratio=0.05)], now_monotonic=1.0)

    assert decision.ai_bear_detected is True
    assert decision.event == "AI_BEAR_DETECTED"


def test_detected_bear_does_not_wait_for_consecutive_approach():
    logic = ApproachLogic(ApproachDetectionConfig(consecutive_required=3))

    first = logic.update([bear_detection()], now_monotonic=1.0)
    second = logic.update([bear_detection()], now_monotonic=1.5)
    third = logic.update([bear_detection()], now_monotonic=2.0)

    assert first.ai_bear_detected is True
    assert second.ai_bear_detected is True
    assert third.ai_bear_detected is True
    assert third.event == "AI_BEAR_DETECTED"


def test_detection_age_gap_resets_consecutive_count():
    logic = ApproachLogic(
        ApproachDetectionConfig(consecutive_required=2, max_detection_age_sec=2.0)
    )

    first = logic.update([bear_detection()], now_monotonic=1.0)
    second = logic.update([bear_detection()], now_monotonic=4.5)

    assert first.consecutive_count == 1
    assert second.consecutive_count == 1
    assert second.ai_bear_detected is True
