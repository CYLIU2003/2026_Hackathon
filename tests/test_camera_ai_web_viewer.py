from pathlib import Path
import sys

CAMERA_AI_DIR = Path(__file__).resolve().parents[1] / "raspberry_pi" / "camera_ai"
sys.path.insert(0, str(CAMERA_AI_DIR))

from web_camera_ai import format_detection_label, terminal_status


def test_format_detection_label_includes_confidence_and_area():
    assert (
        format_detection_label(
            {
                "class_name": "bear",
                "confidence": 0.876,
                "box_area_ratio": 0.125,
            }
        )
        == "bear 0.88 area=12.5%"
    )


def test_terminal_status_is_compact_for_ssh():
    status = terminal_status(
        {
            "timestamp": "2026-06-14T10:00:00+09:00",
            "event": "AI_BEAR_DETECTED",
            "ai_bear_detected": True,
            "ai_bear_approaching": False,
            "ai_bear_confidence": 0.8,
            "inference_time_ms": 123.4,
        }
    )

    assert "event=AI_BEAR_DETECTED" in status
    assert "bear=yes" in status
    assert "approaching=no" in status
