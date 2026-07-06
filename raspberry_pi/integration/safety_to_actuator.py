#!/usr/bin/env python3
"""Bridge presentation safety decisions to the Arduino actuator sketch.

This process watches the Raspberry Pi safety mirror CSV. When the latest row is
fresh and says RELEASE_ON, it sends RELEASE to the Arduino. On RELEASE_OFF,
missing data, stale data, or any read/serial error, it sends STOP or stays safe.

The Arduino contact_pad_controller still owns the field-side state machine and
timeout/cooldown behavior. This bridge is only a demo integration path.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

JST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class LatestDecision:
    ok: bool
    should_release: bool
    message: str
    row: dict


def now_jst_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def latest_csv_row(path: Path) -> Optional[dict]:
    with path.open("r", newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    return rows[-1] if rows else None


def read_latest_decision(path: Path, stale_timeout_sec: float) -> LatestDecision:
    if not path.exists():
        return LatestDecision(False, False, f"missing decision CSV: {path}", {})

    age_sec = time.time() - path.stat().st_mtime
    if age_sec > stale_timeout_sec:
        return LatestDecision(
            False,
            False,
            f"decision CSV stale: {age_sec:.1f}s > {stale_timeout_sec:.1f}s",
            {},
        )

    try:
        row = latest_csv_row(path)
    except (OSError, csv.Error) as exc:
        return LatestDecision(False, False, f"failed to read decision CSV: {exc}", {})

    if not row:
        return LatestDecision(False, False, "decision CSV has no rows", {})

    if parse_bool(row.get("emergency_stop")):
        return LatestDecision(True, False, "emergency_stop active", row)

    if str(row.get("state", "")).strip() == "ERROR_SAFE":
        return LatestDecision(True, False, "safety state is ERROR_SAFE", row)

    should_release = (
        str(row.get("release_state", "")).strip() == "RELEASE_ON"
        or str(row.get("servo_command", "")).strip() == "RELEASE"
    )
    return LatestDecision(True, should_release, "latest decision read", row)


class ArduinoCommandClient:
    def __init__(
        self,
        *,
        port: str,
        baudrate: int,
        timeout: float,
        reset_delay_sec: float,
        no_serial: bool,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.reset_delay_sec = reset_delay_sec
        self.no_serial = no_serial
        self._serial = None

    def connect(self) -> None:
        if self.no_serial or self._serial is not None:
            return
        try:
            import serial  # type: ignore
        except ImportError as exc:
            raise RuntimeError("pyserial is not installed") from exc

        if "://" in self.port:
            self._serial = serial.serial_for_url(
                self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
        else:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
        if self.reset_delay_sec > 0:
            time.sleep(self.reset_delay_sec)

    def send_line(self, command: str) -> str:
        command = command.strip()
        if not command:
            return "EMPTY_COMMAND"
        if self.no_serial:
            return "NO_SERIAL"
        self.connect()
        assert self._serial is not None
        payload = f"{command}\n".encode("utf-8")
        written = self._serial.write(payload)
        self._serial.flush()
        if written != len(payload):
            raise RuntimeError(f"serial write incomplete: {written}/{len(payload)}")
        return "SENT"

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None


def emit_bridge_record(
    *,
    event: str,
    desired_release: bool,
    command: str,
    serial_status: str,
    message: str,
    row: dict,
) -> None:
    record = {
        "timestamp": now_jst_iso(),
        "source": "safety_to_actuator_bridge",
        "event": event,
        "desired_release": desired_release,
        "serial_command": command,
        "serial_status": serial_status,
        "message": message,
        "safety_state": row.get("state", ""),
        "safety_event": row.get("event", ""),
        "release_state": row.get("release_state", ""),
        "servo_command": row.get("servo_command", ""),
    }
    print(json.dumps(record, ensure_ascii=False, separators=(",", ":")), flush=True)


def send_commands(
    client: ArduinoCommandClient,
    commands: list[str],
    *,
    command_delay_sec: float,
) -> tuple[str, str]:
    status = "NO_COMMAND"
    last_command = ""
    for command in commands:
        last_command = command
        status = client.send_line(command)
        if command_delay_sec > 0:
            time.sleep(command_delay_sec)
    return status, last_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send Arduino demo actuator commands from safety mirror CSV."
    )
    parser.add_argument("--input", default="data/logs/feeding_decision_log.csv")
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=0.5)
    parser.add_argument("--serial-reset-delay-sec", type=float, default=2.0)
    parser.add_argument("--poll-interval-sec", type=float, default=0.2)
    parser.add_argument("--stale-timeout-sec", type=float, default=2.0)
    parser.add_argument("--command-delay-sec", type=float, default=0.05)
    parser.add_argument("--no-serial", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--reset-before-release",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Send TEST_AUTO_OFF and RESET before RELEASE for venue demo recovery.",
    )
    parser.add_argument(
        "--stop-on-start",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Send STOP once at startup so the actuator begins closed.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    client = ArduinoCommandClient(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        reset_delay_sec=args.serial_reset_delay_sec,
        no_serial=args.no_serial,
    )
    last_desired_release: Optional[bool] = None

    try:
        if args.stop_on_start:
            status, command = send_commands(
                client,
                ["STOP"],
                command_delay_sec=args.command_delay_sec,
            )
            emit_bridge_record(
                event="STARTUP_STOP",
                desired_release=False,
                command=command,
                serial_status=status,
                message="startup stop sent",
                row={},
            )

        while True:
            decision = read_latest_decision(input_path, args.stale_timeout_sec)
            desired_release = decision.ok and decision.should_release

            commands: list[str] = []
            event = "NO_CHANGE"
            if desired_release and last_desired_release is not True:
                event = "SEND_RELEASE"
                if args.reset_before_release:
                    commands.extend(["TEST_AUTO_OFF", "RESET"])
                commands.append("RELEASE")
            elif not desired_release and last_desired_release is True:
                event = "SEND_STOP"
                commands.append("STOP")
            elif not decision.ok and last_desired_release is None:
                event = "SAFE_NO_DATA"

            serial_status = "NO_COMMAND"
            command = ""
            if commands:
                serial_status, command = send_commands(
                    client,
                    commands,
                    command_delay_sec=args.command_delay_sec,
                )

            if event != "NO_CHANGE" or args.once:
                emit_bridge_record(
                    event=event,
                    desired_release=desired_release,
                    command=command,
                    serial_status=serial_status,
                    message=decision.message,
                    row=decision.row,
                )

            last_desired_release = desired_release
            if args.once:
                break
            time.sleep(args.poll_interval_sec)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        try:
            client.send_line("STOP")
        except Exception:
            pass
        emit_bridge_record(
            event="BRIDGE_ERROR",
            desired_release=False,
            command="STOP",
            serial_status="ERROR",
            message=str(exc),
            row={},
        )
        return 1
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
