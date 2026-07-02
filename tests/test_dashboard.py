import csv
from pathlib import Path

from raspberry_pi.dashboard.app import create_app, find_latest_log_file


class FakeSerial:
    def __init__(self) -> None:
        self.writes: list[str] = []
        self.closed = False

    def write(self, payload: bytes) -> int:
        decoded = payload.decode("utf-8")
        self.writes.append(decoded)
        return len(payload)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


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
    assert b"Feeding Safety Decision" in page_response.data
    assert b"AI_BEAR_DETECTED" in page_response.data
    assert b"RELEASE_OFF" in page_response.data
    assert frame_response.status_code == 200
    assert frame_response.mimetype == "image/jpeg"


def test_dashboard_highlights_integrated_feeding_decision(tmp_path):
    log_dir = tmp_path / "logs"
    frame_dir = tmp_path / "debug_frames"
    feeding_log = log_dir / "feeding_decision_log.csv"
    camera_log = log_dir / "camera_ai_log.csv"
    write_csv(
        feeding_log,
        "timestamp,state,presentation_state,camera_status,bear_detected,"
        "confidence,contact_confirmed,safety_decision,servo_command,"
        "log_status,input_mode",
        "2026-06-24T18:50:12+09:00,RELEASING,FEEDING,Running,true,"
        "0.86,true,SAFE_TO_FEED,RELEASE,SAVED,camera",
    )
    write_csv(camera_log, "timestamp,event", "2026-06-24T18:50:12+09:00,AI_BEAR_APPROACHING")

    app = create_app(
        log_dir,
        str(feeding_log),
        1,
        camera_log_file=str(camera_log),
        debug_frame_dir=frame_dir,
        camera_frame_file="latest_camera_ai.jpg",
    )
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"FEEDING" in response.data
    assert b"SAFE_TO_FEED" in response.data
    assert b"RELEASE" in response.data
    assert b"Confirmed" in response.data


def test_dashboard_shows_demo_mode_panel_and_status_api(tmp_path):
    log_dir = tmp_path / "logs"
    frame_dir = tmp_path / "debug_frames"
    demo_log = log_dir / "demo_commands.csv"

    app = create_app(
        log_dir,
        "",
        1,
        camera_log_file=str(log_dir / "camera_ai_log.csv"),
        debug_frame_dir=frame_dir,
        camera_frame_file="latest_camera_ai.jpg",
        demo_command_log_file=str(demo_log),
        demo_force_simulation=True,
    )
    client = app.test_client()

    page_response = client.get("/")
    status_response = client.get("/api/demo-status")

    assert page_response.status_code == 200
    assert b"Demo Mode" in page_response.data
    assert b"Release / Open" in page_response.data
    assert b"Stop / Close" in page_response.data
    assert b"Test Motion" in page_response.data
    assert b"Emergency Stop" in page_response.data
    assert status_response.status_code == 200
    assert status_response.json["demo_enabled"] is False
    assert status_response.json["last_command"] == "STOP"
    assert status_response.json["result"] == "DEFAULT_CLOSED"


def test_demo_command_requires_enable_and_logs_simulated_commands(tmp_path):
    log_dir = tmp_path / "logs"
    frame_dir = tmp_path / "debug_frames"
    demo_log = log_dir / "demo_commands.csv"
    app = create_app(
        log_dir,
        "",
        1,
        camera_log_file=str(log_dir / "camera_ai_log.csv"),
        debug_frame_dir=frame_dir,
        camera_frame_file="latest_camera_ai.jpg",
        demo_command_log_file=str(demo_log),
        demo_force_simulation=True,
    )
    client = app.test_client()

    blocked_response = client.post("/api/demo-command", json={"command": "RELEASE"})
    enable_response = client.post("/api/demo-mode", json={"enabled": True})
    command_response = client.post("/api/demo-command", json={"command": "TEST"})

    assert blocked_response.status_code == 403
    assert blocked_response.json["result"] == "BLOCKED"
    assert blocked_response.json["last_command"] == "RELEASE"
    assert enable_response.status_code == 200
    assert enable_response.json["demo_enabled"] is True
    assert enable_response.json["last_command"] == "STOP"
    assert command_response.status_code == 200
    assert command_response.json["result"] == "SIMULATED"
    assert command_response.json["last_command"] == "TEST"
    assert command_response.json["simulation_mode"] is True

    with demo_log.open("r", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert [row["command"] for row in rows] == ["RELEASE", "STOP", "TEST"]
    assert [row["serial_command"] for row in rows] == ["", "STOP", "TEST"]
    assert rows[0]["result"] == "BLOCKED"
    assert rows[-1]["result"] == "SIMULATED"


def test_demo_release_sends_serial_command_after_enable(tmp_path):
    log_dir = tmp_path / "logs"
    frame_dir = tmp_path / "debug_frames"
    fake_serial = FakeSerial()

    def fake_factory(port: str, baudrate: int, timeout: float, write_timeout: float):
        return fake_serial

    app = create_app(
        log_dir,
        "",
        1,
        camera_log_file=str(log_dir / "camera_ai_log.csv"),
        debug_frame_dir=frame_dir,
        camera_frame_file="latest_camera_ai.jpg",
        demo_command_log_file=str(log_dir / "demo_commands.csv"),
        demo_serial_reset_delay=0,
        serial_client_factory=fake_factory,
    )
    client = app.test_client()

    enable_response = client.post("/api/demo-mode", json={"enabled": True})
    release_response = client.post("/api/demo-command", json={"command": "RELEASE"})

    assert enable_response.status_code == 200
    assert release_response.status_code == 200
    assert release_response.json["result"] == "SENT"
    assert release_response.json["serial_status"] == "CONNECTED"
    assert fake_serial.writes == ["STOP\n", "RELEASE\n"]


def test_demo_stop_is_available_without_enable(tmp_path):
    log_dir = tmp_path / "logs"
    demo_log = log_dir / "demo_commands.csv"
    app = create_app(
        log_dir,
        "",
        1,
        camera_log_file=str(log_dir / "camera_ai_log.csv"),
        debug_frame_dir=tmp_path / "debug_frames",
        camera_frame_file="latest_camera_ai.jpg",
        demo_command_log_file=str(demo_log),
        demo_force_simulation=True,
    )

    response = app.test_client().post("/api/demo-command", json={"command": "STOP"})

    assert response.status_code == 200
    assert response.json["demo_enabled"] is False
    assert response.json["last_command"] == "STOP"
    assert response.json["result"] == "SIMULATED"

    with demo_log.open("r", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert rows[-1]["command"] == "STOP"
    assert rows[-1]["serial_command"] == "STOP"


def test_emergency_stop_sends_stop_and_disables_demo(tmp_path):
    log_dir = tmp_path / "logs"
    frame_dir = tmp_path / "debug_frames"
    fake_serial = FakeSerial()

    def fake_factory(port: str, baudrate: int, timeout: float, write_timeout: float):
        return fake_serial

    app = create_app(
        log_dir,
        "",
        1,
        camera_log_file=str(log_dir / "camera_ai_log.csv"),
        debug_frame_dir=frame_dir,
        camera_frame_file="latest_camera_ai.jpg",
        demo_command_log_file=str(log_dir / "demo_commands.csv"),
        demo_serial_reset_delay=0,
        serial_client_factory=fake_factory,
    )
    client = app.test_client()

    client.post("/api/demo-mode", json={"enabled": True})
    response = client.post("/api/demo-command", json={"command": "EMERGENCY_STOP"})

    assert response.status_code == 200
    assert response.json["last_command"] == "STOP"
    assert response.json["requested_command"] == "EMERGENCY_STOP"
    assert response.json["demo_enabled"] is False
    assert fake_serial.writes == ["STOP\n", "STOP\n"]


def test_demo_command_uses_simulation_when_serial_is_unavailable(tmp_path):
    log_dir = tmp_path / "logs"
    frame_dir = tmp_path / "debug_frames"
    demo_log = log_dir / "demo_commands.csv"

    def unavailable_factory(port: str, baudrate: int, timeout: float, write_timeout: float):
        raise OSError("port not found")

    app = create_app(
        log_dir,
        "",
        1,
        camera_log_file=str(log_dir / "camera_ai_log.csv"),
        debug_frame_dir=frame_dir,
        camera_frame_file="latest_camera_ai.jpg",
        demo_command_log_file=str(demo_log),
        demo_serial_reset_delay=0,
        serial_client_factory=unavailable_factory,
    )
    client = app.test_client()

    enable_response = client.post("/api/demo-mode", json={"enabled": True})
    release_response = client.post("/api/demo-command", json={"command": "RELEASE"})

    assert enable_response.status_code == 200
    assert enable_response.json["result"] == "SIMULATED"
    assert release_response.status_code == 200
    assert release_response.json["result"] == "SIMULATED"
    assert release_response.json["serial_status"] == "SIMULATION_MODE"
    assert "serial unavailable" in release_response.json["message"]

    with demo_log.open("r", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert rows[-1]["command"] == "RELEASE"
    assert rows[-1]["serial_command"] == "RELEASE"


def test_demo_command_timeout_returns_error(tmp_path):
    log_dir = tmp_path / "logs"
    demo_log = log_dir / "demo_commands.csv"

    def timeout_factory(port: str, baudrate: int, timeout: float, write_timeout: float):
        raise TimeoutError("write timeout")

    app = create_app(
        log_dir,
        "",
        1,
        camera_log_file=str(log_dir / "camera_ai_log.csv"),
        debug_frame_dir=tmp_path / "debug_frames",
        camera_frame_file="latest_camera_ai.jpg",
        demo_command_log_file=str(demo_log),
        demo_serial_reset_delay=0,
        serial_client_factory=timeout_factory,
    )

    response = app.test_client().post("/api/demo-mode", json={"enabled": True})

    assert response.status_code == 504
    assert response.json["result"] == "ERROR"
    assert response.json["serial_status"] == "ERROR"
    assert "timeout" in response.json["message"].lower()

    with demo_log.open("r", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert rows[-1]["serial_command"] == "STOP"
    assert rows[-1]["result"] == "ERROR"


def test_invalid_demo_command_returns_error_and_logs(tmp_path):
    log_dir = tmp_path / "logs"
    demo_log = log_dir / "demo_commands.csv"
    app = create_app(
        log_dir,
        "",
        1,
        camera_log_file=str(log_dir / "camera_ai_log.csv"),
        debug_frame_dir=tmp_path / "debug_frames",
        camera_frame_file="latest_camera_ai.jpg",
        demo_command_log_file=str(demo_log),
        demo_force_simulation=True,
    )

    response = app.test_client().post(
        "/api/demo-command",
        json={"command": "DANCE"},
    )

    assert response.status_code == 400
    assert response.json["result"] == "ERROR"
    assert response.json["requested_command"] == "DANCE"

    with demo_log.open("r", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert rows[-1]["command"] == "DANCE"
    assert rows[-1]["result"] == "ERROR"


def test_dashboard_excludes_demo_command_log_from_latest_contact_log(tmp_path):
    log_dir = tmp_path / "logs"
    frame_dir = tmp_path / "debug_frames"
    contact_log = log_dir / "contact_pad_log.csv"
    demo_log = log_dir / "demo_commands.csv"
    write_csv(
        contact_log,
        "timestamp,state,event,release_state",
        "2026-06-17T10:00:00+09:00,IDLE,CONTACT_SENSOR_OK,RELEASE_OFF",
    )
    write_csv(
        demo_log,
        "timestamp,command,result",
        "2026-06-17T10:01:00+09:00,RELEASE,SIMULATED",
    )

    app = create_app(
        log_dir,
        "",
        1,
        camera_log_file=str(log_dir / "camera_ai_log.csv"),
        debug_frame_dir=frame_dir,
        camera_frame_file="latest_camera_ai.jpg",
        demo_command_log_file=str(demo_log),
        demo_force_simulation=True,
    )

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"CONTACT_SENSOR_OK" in response.data
