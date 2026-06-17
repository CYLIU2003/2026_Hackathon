from pathlib import Path

from raspberry_pi.dashboard.app import create_app, find_latest_log_file


def write_csv(path: Path, header: str, row: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{header}\n{row}\n", encoding="utf-8")


def test_latest_contact_log_excludes_camera_ai_log(tmp_path):
    log_dir = tmp_path / "logs"
    contact_log = log_dir / "contact_pad_log.csv"
    camera_log = log_dir / "camera_ai_log.csv"
    write_csv(contact_log, "timestamp,event", "2026-06-17T10:00:00+09:00,IDLE")
    write_csv(camera_log, "timestamp,event", "2026-06-17T10:01:00+09:00,AI_NO_BEAR")

    selected_log = find_latest_log_file(
        log_dir,
        excluded_names={"camera_ai_log.csv"},
    )

    assert selected_log == contact_log


def test_dashboard_serves_camera_ai_state_and_latest_frame(tmp_path):
    log_dir = tmp_path / "logs"
    frame_dir = tmp_path / "debug_frames"
    contact_log = log_dir / "contact_pad_log.csv"
    camera_log = log_dir / "camera_ai_log.csv"
    frame_path = frame_dir / "latest_camera_ai.jpg"
    write_csv(
        contact_log,
        "timestamp,state,event,release_state",
        "2026-06-17T10:00:00+09:00,IDLE,IDLE,RELEASE_OFF",
    )
    write_csv(
        camera_log,
        "timestamp,event,ai_camera_ok,ai_model_ok,ai_bear_detected,ai_bear_approaching",
        "2026-06-17T10:01:00+09:00,AI_BEAR_DETECTED,true,true,true,false",
    )
    frame_dir.mkdir(parents=True)
    frame_path.write_bytes(b"\xff\xd8\xff\xd9")

    app = create_app(
        log_dir,
        "",
        1,
        camera_log_file=str(camera_log),
        debug_frame_dir=frame_dir,
        camera_frame_file="latest_camera_ai.jpg",
    )
    client = app.test_client()

    page_response = client.get("/")
    frame_response = client.get("/camera/latest.jpg")

    assert page_response.status_code == 200
    assert b"Camera AI View" in page_response.data
    assert b"AI_BEAR_DETECTED" in page_response.data
    assert b"RELEASE_OFF" in page_response.data
    assert frame_response.status_code == 200
    assert frame_response.mimetype == "image/jpeg"
