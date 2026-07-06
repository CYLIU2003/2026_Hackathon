import csv
import subprocess
import sys
from pathlib import Path

from raspberry_pi.integration.safety_to_actuator import read_latest_decision


FIELDNAMES = [
    "timestamp",
    "state",
    "event",
    "release_state",
    "servo_command",
    "emergency_stop",
]


def write_decision(path: Path, **values):
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": "2026-07-06T11:30:00+09:00",
        "state": "RELEASING",
        "event": "RELEASE_START",
        "release_state": "RELEASE_ON",
        "servo_command": "RELEASE",
        "emergency_stop": "false",
    }
    row.update(values)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerow(row)


def test_latest_decision_release_on_requests_release(tmp_path):
    decision_path = tmp_path / "feeding_decision_log.csv"
    write_decision(decision_path)

    decision = read_latest_decision(decision_path, stale_timeout_sec=60.0)

    assert decision.ok is True
    assert decision.should_release is True


def test_latest_decision_error_safe_blocks_release(tmp_path):
    decision_path = tmp_path / "feeding_decision_log.csv"
    write_decision(
        decision_path,
        state="ERROR_SAFE",
        event="ERROR_SAFE",
        release_state="RELEASE_ON",
        servo_command="RELEASE",
    )

    decision = read_latest_decision(decision_path, stale_timeout_sec=60.0)

    assert decision.ok is True
    assert decision.should_release is False


def test_bridge_once_no_serial_emits_release_command(tmp_path):
    decision_path = tmp_path / "feeding_decision_log.csv"
    write_decision(decision_path)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "raspberry_pi.integration.safety_to_actuator",
            "--input",
            str(decision_path),
            "--no-serial",
            "--once",
            "--no-stop-on-start",
            "--serial-reset-delay-sec",
            "0",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert '"event":"SEND_RELEASE"' in completed.stdout
    assert '"serial_command":"RELEASE"' in completed.stdout
