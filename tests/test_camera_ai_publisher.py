from raspberry_pi.camera_ai.ai_state_publisher import (
    CSV_COLUMNS,
    AiState,
    AiStatePublisher,
)


def test_camera_ai_csv_schema_change_rotates_legacy_log(tmp_path):
    csv_path = tmp_path / "camera_ai_log.csv"
    csv_path.write_text(
        "timestamp,source,camera_device,ai_camera_ok,ai_model_ok,"
        "ai_bear_detected,ai_bear_confidence,ai_bear_box_area_ratio,"
        "ai_bear_approaching,event,inference_time_ms\n"
        "old,camera_ai,/dev/video0,true,true,true,0.8,0.1,true,"
        "AI_BEAR_APPROACHING,1.0\n",
        encoding="utf-8",
    )
    publisher = AiStatePublisher(jsonl_stdout=False, save_csv=True, csv_path=csv_path)

    publisher.publish(
        AiState(
            timestamp="2026-07-06T14:40:00+09:00",
            camera_device="/dev/video0",
            ai_camera_ok=True,
            ai_model_ok=True,
            ai_bear_detected=True,
            ai_bear_confidence=0.8,
            ai_bear_box_area_ratio=0.1,
            event="AI_BEAR_DETECTED",
            inference_time_ms=1.0,
        )
    )

    legacy_logs = list(tmp_path.glob("camera_ai_log.legacy_*.csv"))
    assert len(legacy_logs) == 1
    assert csv_path.read_text(encoding="utf-8").splitlines()[0] == ",".join(
        CSV_COLUMNS
    )
    assert "ai_bear_approaching" not in csv_path.read_text(encoding="utf-8")
