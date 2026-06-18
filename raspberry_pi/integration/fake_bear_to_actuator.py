#!/usr/bin/env python3
"""
Fake Raspberry Pi Camera AI -> Arduino actuator integration demo.

This script is intentionally runnable on Raspberry Pi, Windows, macOS, or Linux.
It simulates a camera AI module that repeatedly detects a bear and sends safe
serial commands to the Arduino contact_pad_controller sketch.

Use cases:
  1. Goda-san does not have a Raspberry Pi but has Arduino + PCA9685 + servo.
  2. The team wants to confirm actuator integration before YOLO is ready.
  3. The team wants JSON Lines that look like camera AI output.

Examples:
  Windows:
    python raspberry_pi/integration/fake_bear_to_actuator.py --port COM3 --loop

  Raspberry Pi / Linux:
    python3 raspberry_pi/integration/fake_bear_to_actuator.py --port /dev/ttyACM0 --loop

  JSON Lines only, no serial hardware:
    python3 raspberry_pi/integration/fake_bear_to_actuator.py --no-serial --loop
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Iterable, Optional

JST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class FakeDetectionState:
    name: str
    ai_bear_detected: bool
    ai_bear_approaching: bool
    paw_contact: bool
    honey_amount_percent: int
    system_safe: bool
    emergency_stop: bool
    duration_sec: float


def now_jst_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def emit_jsonl(state: FakeDetectionState, step_index: int) -> None:
    record = {
        "timestamp": now_jst_iso(),
        "source": "fake_camera_ai",
        "mode": "test_without_real_raspberry_pi_or_yolo",
        "step_index": step_index,
        "step_name": state.name,
        "ai_camera_ok": True,
        "ai_model_ok": True,
        "ai_bear_detected": state.ai_bear_detected,
        "ai_bear_confidence": 0.92 if state.ai_bear_detected else 0.0,
        "ai_bear_box_area_ratio": 0.22 if state.ai_bear_detected else 0.0,
        "ai_bear_approaching": state.ai_bear_approaching,
        "paw_contact": state.paw_contact,
        "honey_amount_percent": state.honey_amount_percent,
        "system_safe": state.system_safe,
        "emergency_stop": state.emergency_stop,
        "event": "AI_BEAR_APPROACHING" if state.ai_bear_approaching else "AI_IDLE",
    }
    print(json.dumps(record, ensure_ascii=False), flush=True)


def serial_commands_for_state(state: FakeDetectionState) -> list[str]:
    commands = [
        "TEST_AUTO_OFF",
        f"SET AI_BEAR {1 if state.ai_bear_approaching else 0}",
        f"SET PAW {1 if state.paw_contact else 0}",
        f"SET HONEY {int(state.honey_amount_percent)}",
        f"SET SAFE {1 if state.system_safe else 0}",
        f"SET ESTOP {1 if state.emergency_stop else 0}",
        "STATUS",
    ]
    if not state.emergency_stop:
        commands.insert(1, "RESET")
    return commands


class SerialWriter:
    def __init__(self, port: str, baudrate: int, timeout: float) -> None:
        try:
            import serial  # type: ignore
        except ImportError as exc:
            raise SystemExit(
                "pyserial is required for serial mode. Install it with: python -m pip install pyserial"
            ) from exc

        self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        # Give Arduino time to reset after opening serial.
        time.sleep(2.0)

    def write_line(self, line: str) -> None:
        payload = (line.strip() + "\n").encode("utf-8")
        self._serial.write(payload)
        self._serial.flush()

    def read_available(self) -> list[str]:
        lines: list[str] = []
        while self._serial.in_waiting:
            raw = self._serial.readline().decode("utf-8", errors="replace").strip()
            if raw:
                lines.append(raw)
        return lines

    def close(self) -> None:
        self._serial.close()


def default_scenario() -> list[FakeDetectionState]:
    return [
        FakeDetectionState(
            name="idle_no_bear",
            ai_bear_detected=False,
            ai_bear_approaching=False,
            paw_contact=False,
            honey_amount_percent=80,
            system_safe=True,
            emergency_stop=False,
            duration_sec=2.0,
        ),
        FakeDetectionState(
            name="bear_detected_no_contact",
            ai_bear_detected=True,
            ai_bear_approaching=True,
            paw_contact=False,
            honey_amount_percent=80,
            system_safe=True,
            emergency_stop=False,
            duration_sec=2.0,
        ),
        FakeDetectionState(
            name="bear_detected_contact_release_allowed",
            ai_bear_detected=True,
            ai_bear_approaching=True,
            paw_contact=True,
            honey_amount_percent=80,
            system_safe=True,
            emergency_stop=False,
            duration_sec=6.0,
        ),
        FakeDetectionState(
            name="cooldown_no_contact",
            ai_bear_detected=True,
            ai_bear_approaching=True,
            paw_contact=False,
            honey_amount_percent=80,
            system_safe=True,
            emergency_stop=False,
            duration_sec=3.0,
        ),
        FakeDetectionState(
            name="honey_low_no_release",
            ai_bear_detected=True,
            ai_bear_approaching=True,
            paw_contact=True,
            honey_amount_percent=10,
            system_safe=True,
            emergency_stop=False,
            duration_sec=3.0,
        ),
        FakeDetectionState(
            name="emergency_stop_safe_close",
            ai_bear_detected=True,
            ai_bear_approaching=True,
            paw_contact=True,
            honey_amount_percent=80,
            system_safe=True,
            emergency_stop=True,
            duration_sec=3.0,
        ),
    ]


def run_scenario(
    scenario: Iterable[FakeDetectionState],
    serial_writer: Optional[SerialWriter],
    loop: bool,
    command_interval_sec: float,
) -> None:
    step_index = 0

    while True:
        for state in scenario:
            step_index += 1
            emit_jsonl(state, step_index)

            if serial_writer is not None:
                for command in serial_commands_for_state(state):
                    serial_writer.write_line(command)
                    time.sleep(command_interval_sec)

                for line in serial_writer.read_available():
                    print(f"[arduino] {line}", file=sys.stderr, flush=True)

            time.sleep(state.duration_sec)

        if not loop:
            break


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fake Camera AI and send simulated bear/contact/safety states to Arduino."
    )
    parser.add_argument("--port", help="Serial port, e.g. COM3 or /dev/ttyACM0")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=0.2)
    parser.add_argument("--no-serial", action="store_true", help="Only print fake camera JSON Lines")
    parser.add_argument("--loop", action="store_true", help="Repeat the scenario forever")
    parser.add_argument("--command-interval-sec", type=float, default=0.05)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    serial_writer: Optional[SerialWriter] = None
    if not args.no_serial:
        if not args.port:
            print("ERROR: --port is required unless --no-serial is used", file=sys.stderr)
            return 2
        serial_writer = SerialWriter(args.port, args.baudrate, args.timeout)

    try:
        run_scenario(
            scenario=default_scenario(),
            serial_writer=serial_writer,
            loop=args.loop,
            command_interval_sec=args.command_interval_sec,
        )
    finally:
        if serial_writer is not None:
            serial_writer.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
