from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


CSV_FIELDS = [
    "timestamp",
    "source",
    "input_mode",
    "scenario_step",
    "state",
    "presentation_state",
    "previous_state",
    "event",
    "camera_status",
    "bear_detected",
    "confidence",
    "bear_box_area_ratio",
    "contact_detected",
    "contact_confirmed",
    "impedance_kohm",
    "honey_amount_percent",
    "honey_enough",
    "system_safe",
    "emergency_stop",
    "safety_decision",
    "release_allowed",
    "release_state",
    "servo_command",
    "log_status",
    "sensor_input_mode",
    "error_code",
    "error_message",
]


class State(str, Enum):
    IDLE = "IDLE"
    BEAR_DETECTED = "BEAR_DETECTED"
    CONTACT_CONFIRMED = "CONTACT_CONFIRMED"
    READY_TO_RELEASE = "READY_TO_RELEASE"
    RELEASING = "RELEASING"
    COOLDOWN = "COOLDOWN"
    ERROR_SAFE = "ERROR_SAFE"


@dataclass(frozen=True)
class SafetyConfig:
    honey_min_threshold_percent: int
    contact_confirm_duration_ms: int
    max_release_duration_ms: int
    cooldown_after_release_ms: int
    camera_data_timeout_ms: int
    log_interval_ms: int
    default_honey_amount_percent: int

    @classmethod
    def load(cls, path: Path) -> "SafetyConfig":
        values = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            honey_min_threshold_percent=int(values["honey_min_threshold_percent"]),
            contact_confirm_duration_ms=int(values["contact_confirm_duration_ms"]),
            max_release_duration_ms=int(values["max_release_duration_ms"]),
            cooldown_after_release_ms=int(values["cooldown_after_release_ms"]),
            camera_data_timeout_ms=int(values["camera_data_timeout_ms"]),
            log_interval_ms=int(values["log_interval_ms"]),
            default_honey_amount_percent=int(
                values["default_honey_amount_percent"]
            ),
        )


@dataclass(frozen=True)
class SensorSnapshot:
    bear_detected: bool
    confidence: Optional[float]
    bear_box_area_ratio: Optional[float]
    contact_detected: bool
    impedance_kohm: Optional[float]
    honey_amount_percent: int
    system_safe: bool
    emergency_stop: bool
    source_ok: bool = True
    source_error: str = ""
    scenario_step: str = ""
    reset_requested: bool = False


class SafetyStateMachine:
    def __init__(self, config: SafetyConfig) -> None:
        self.config = config
        self.state = State.IDLE
        self.previous_state = State.IDLE
        self.event = "BOOT"
        self.error_code = "ERR_NONE"
        self.error_message = ""
        self._contact_started_ms: Optional[int] = None
        self._release_started_ms: Optional[int] = None
        self._cooldown_started_ms: Optional[int] = None

    def reset(self, now_ms: int) -> None:
        self.previous_state = self.state
        self.state = State.IDLE
        self.event = "RESET"
        self.error_code = "ERR_NONE"
        self.error_message = ""
        self._contact_started_ms = None
        self._release_started_ms = None
        self._cooldown_started_ms = None

    def update(self, inputs: SensorSnapshot, now_ms: int) -> dict:
        if inputs.reset_requested and self.state == State.ERROR_SAFE:
            self.reset(now_ms)

        contact_confirmed = self._update_contact_confirmation(inputs, now_ms)
        honey_valid = 0 <= inputs.honey_amount_percent <= 100
        honey_enough = (
            honey_valid
            and inputs.honey_amount_percent
            >= self.config.honey_min_threshold_percent
        )

        if not inputs.source_ok:
            self._enter_error(
                "ERR_INPUT_SOURCE",
                inputs.source_error or "input source unavailable",
            )
        elif not honey_valid:
            self._enter_error(
                "ERR_INVALID_HONEY_AMOUNT",
                "honey_amount_percent must be between 0 and 100",
            )
        elif inputs.emergency_stop:
            self._enter_error("ERR_EMERGENCY_STOP", "emergency_stop active")

        release_allowed = (
            inputs.bear_detected
            and contact_confirmed
            and honey_enough
            and inputs.system_safe
            and not inputs.emergency_stop
            and inputs.source_ok
            and self.state != State.ERROR_SAFE
        )

        if self.state != State.ERROR_SAFE:
            self._advance(
                inputs=inputs,
                contact_confirmed=contact_confirmed,
                honey_enough=honey_enough,
                release_allowed=release_allowed,
                now_ms=now_ms,
            )

        release_on = self.state == State.RELEASING and release_allowed
        safety_decision = self._safety_decision(
            inputs, contact_confirmed, honey_enough, release_on
        )
        return {
            "state": self.state.value,
            "previous_state": self.previous_state.value,
            "event": self.event,
            "contact_confirmed": contact_confirmed,
            "honey_enough": honey_enough,
            "release_allowed": release_allowed,
            "safety_decision": safety_decision,
            "release_state": "RELEASE_ON" if release_on else "RELEASE_OFF",
            "servo_command": "RELEASE" if release_on else "HOLD",
            "error_code": self.error_code,
            "error_message": self.error_message,
        }

    def _update_contact_confirmation(
        self, inputs: SensorSnapshot, now_ms: int
    ) -> bool:
        if not inputs.contact_detected:
            self._contact_started_ms = None
            return False
        if self._contact_started_ms is None:
            self._contact_started_ms = now_ms
        return (
            now_ms - self._contact_started_ms
            >= self.config.contact_confirm_duration_ms
        )

    def _advance(
        self,
        *,
        inputs: SensorSnapshot,
        contact_confirmed: bool,
        honey_enough: bool,
        release_allowed: bool,
        now_ms: int,
    ) -> None:
        if self.state == State.IDLE:
            if inputs.bear_detected:
                self._enter(State.BEAR_DETECTED, "BEAR_DETECTED", now_ms)
        elif self.state == State.BEAR_DETECTED:
            if not inputs.bear_detected:
                self._enter(State.IDLE, "NO_BEAR", now_ms)
            elif contact_confirmed:
                self._enter(State.CONTACT_CONFIRMED, "CONTACT_CONFIRMED", now_ms)
        elif self.state == State.CONTACT_CONFIRMED:
            if not inputs.bear_detected:
                self._enter(State.IDLE, "NO_BEAR", now_ms)
            elif not contact_confirmed:
                self._enter(State.BEAR_DETECTED, "WAIT_CONTACT", now_ms)
            elif release_allowed:
                self._enter(State.READY_TO_RELEASE, "SAFE_TO_FEED", now_ms)
            elif not honey_enough:
                self.event = "HONEY_LOW"
            elif not inputs.system_safe:
                self.event = "SYSTEM_UNSAFE"
        elif self.state == State.READY_TO_RELEASE:
            if release_allowed:
                self._enter(State.RELEASING, "RELEASE_START", now_ms)
            else:
                self._enter(State.CONTACT_CONFIRMED, "RELEASE_BLOCKED", now_ms)
        elif self.state == State.RELEASING:
            release_elapsed = now_ms - (self._release_started_ms or now_ms)
            if not release_allowed:
                self._enter(State.COOLDOWN, "RELEASE_ABORTED", now_ms)
            elif release_elapsed >= self.config.max_release_duration_ms:
                self._enter(State.COOLDOWN, "RELEASE_TIMEOUT", now_ms)
        elif self.state == State.COOLDOWN:
            cooldown_elapsed = now_ms - (self._cooldown_started_ms or now_ms)
            if cooldown_elapsed >= self.config.cooldown_after_release_ms:
                self._enter(State.IDLE, "COOLDOWN_END", now_ms)

    def _enter(self, state: State, event: str, now_ms: int) -> None:
        if self.state == state:
            self.event = event
            return
        self.previous_state = self.state
        self.state = state
        self.event = event
        if state == State.RELEASING:
            self._release_started_ms = now_ms
        if state == State.COOLDOWN:
            self._cooldown_started_ms = now_ms

    def _enter_error(self, code: str, message: str) -> None:
        if self.state != State.ERROR_SAFE:
            self.previous_state = self.state
        self.state = State.ERROR_SAFE
        self.event = "ERROR_SAFE"
        self.error_code = code
        self.error_message = message

    def _safety_decision(
        self,
        inputs: SensorSnapshot,
        contact_confirmed: bool,
        honey_enough: bool,
        release_on: bool,
    ) -> str:
        if self.state == State.ERROR_SAFE:
            return "ERROR_SAFE"
        if self.state == State.COOLDOWN:
            return "COOLDOWN"
        if release_on or self.state == State.READY_TO_RELEASE:
            return "SAFE_TO_FEED"
        if not inputs.bear_detected:
            return "IDLE"
        if not contact_confirmed:
            return "WAIT_CONTACT"
        if not honey_enough:
            return "HOLD_HONEY_LOW"
        if not inputs.system_safe:
            return "HOLD_UNSAFE"
        return "HOLD"

class ScenarioInput:
    def __init__(self, config: SafetyConfig) -> None:
        self.config = config
        self._started = time.monotonic()

    def read(self) -> SensorSnapshot:
        elapsed = (time.monotonic() - self._started) % 24.0
        reset_requested = elapsed < 0.7
        if elapsed < 3.0:
            return self._snapshot("IDLE", False, False, reset_requested=reset_requested)
        if elapsed < 6.0:
            return self._snapshot("BEAR_DETECTED", True, False)
        if elapsed < 12.0:
            return self._snapshot("CONTACT_AND_FEED", True, True)
        if elapsed < 17.5:
            return self._snapshot("COOLDOWN", False, False)
        if elapsed < 21.0:
            return self._snapshot("HONEY_LOW", True, True, honey=10)
        return self._snapshot("SYSTEM_UNSAFE", True, True, system_safe=False)

    def _snapshot(
        self,
        step: str,
        bear: bool,
        contact: bool,
        *,
        honey: Optional[int] = None,
        system_safe: bool = True,
        reset_requested: bool = False,
    ) -> SensorSnapshot:
        return SensorSnapshot(
            bear_detected=bear,
            confidence=0.86 if bear else None,
            bear_box_area_ratio=0.18 if bear else None,
            contact_detected=contact,
            impedance_kohm=92.4 if contact else None,
            honey_amount_percent=(
                self.config.default_honey_amount_percent
                if honey is None
                else honey
            ),
            system_safe=system_safe,
            emergency_stop=False,
            scenario_step=step,
            reset_requested=reset_requested,
        )


class CameraCsvInput:
    def __init__(
        self,
        camera_log_path: Path,
        config: SafetyConfig,
        *,
        mock_contact: bool,
        mock_impedance_kohm: float,
        honey_amount_percent: int,
        system_safe: bool,
        emergency_stop: bool,
    ) -> None:
        self.camera_log_path = camera_log_path
        self.config = config
        self.mock_contact = mock_contact
        self.mock_impedance_kohm = mock_impedance_kohm
        self.honey_amount_percent = honey_amount_percent
        self.system_safe = system_safe
        self.emergency_stop = emergency_stop
        self._reset_after_recovery = False

    def read(self) -> SensorSnapshot:
        if not self.camera_log_path.exists():
            return self._error("camera AI log is missing")
        age_ms = (time.time() - self.camera_log_path.stat().st_mtime) * 1000.0
        if age_ms > self.config.camera_data_timeout_ms:
            return self._error("camera AI data timed out")
        try:
            with self.camera_log_path.open("r", newline="", encoding="utf-8") as handle:
                row = next(reversed(list(csv.DictReader(handle))), None)
        except (OSError, csv.Error) as exc:
            return self._error(f"camera AI log read failed: {exc}")
        if not row:
            return self._error("camera AI log has no records")

        camera_ok = parse_bool(row.get("ai_camera_ok"))
        model_ok = parse_bool(row.get("ai_model_ok"))
        if not camera_ok or not model_ok:
            return self._error("camera or model is not ready")

        bear_detected = parse_bool(row.get("ai_bear_detected"))
        contact = self.mock_contact and bear_detected
        reset_requested = self._reset_after_recovery
        self._reset_after_recovery = False
        return SensorSnapshot(
            bear_detected=bear_detected,
            confidence=parse_optional_float(row.get("ai_bear_confidence")),
            bear_box_area_ratio=parse_optional_float(
                row.get("ai_bear_box_area_ratio")
            ),
            contact_detected=contact,
            impedance_kohm=self.mock_impedance_kohm if contact else None,
            honey_amount_percent=self.honey_amount_percent,
            system_safe=self.system_safe,
            emergency_stop=self.emergency_stop,
            scenario_step="LIVE_CAMERA",
            reset_requested=reset_requested,
        )

    def _error(self, message: str) -> SensorSnapshot:
        self._reset_after_recovery = True
        return SensorSnapshot(
            bear_detected=False,
            confidence=None,
            bear_box_area_ratio=None,
            contact_detected=False,
            impedance_kohm=None,
            honey_amount_percent=self.honey_amount_percent,
            system_safe=False,
            emergency_stop=False,
            source_ok=False,
            source_error=message,
            scenario_step="CAMERA_ERROR",
        )


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_optional_float(value: object) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def now_iso8601() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def append_csv(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rotate_csv_if_schema_changed(path)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def rotate_csv_if_schema_changed(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return
    try:
        with path.open("r", newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle), [])
    except (OSError, csv.Error):
        return
    if header == CSV_FIELDS:
        return
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%dT%H%M%S%z")
    legacy_path = path.with_name(f"{path.stem}.legacy_{timestamp}{path.suffix}")
    path.rename(legacy_path)


def describe_camera_status(inputs: SensorSnapshot, input_mode: str) -> str:
    if input_mode == "scenario":
        return "Simulated input / シミュレーション入力"
    if not inputs.source_ok:
        return "Camera error / カメラ異常"
    if inputs.bear_detected:
        return "Detected / 検出済み"
    return "No bear detected / 熊未検出"


def build_record(
    inputs: SensorSnapshot,
    decision: dict,
    *,
    input_mode: str,
) -> dict:
    state = decision["state"]
    return {
        "timestamp": now_iso8601(),
        "source": "safety_control_demo_mirror",
        "input_mode": input_mode,
        "scenario_step": inputs.scenario_step,
        "presentation_state": {
            "READY_TO_RELEASE": "SAFE_TO_FEED",
            "RELEASING": "FEEDING",
        }.get(state, state),
        "camera_status": describe_camera_status(inputs, input_mode),
        "bear_detected": inputs.bear_detected,
        "confidence": inputs.confidence,
        "bear_box_area_ratio": inputs.bear_box_area_ratio,
        "contact_detected": inputs.contact_detected,
        "impedance_kohm": inputs.impedance_kohm,
        "honey_amount_percent": inputs.honey_amount_percent,
        "system_safe": inputs.system_safe,
        "emergency_stop": inputs.emergency_stop,
        "sensor_input_mode": "MOCK",
        "log_status": "SAVED",
        **decision,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the presentation-side safe feeding decision mirror."
    )
    parser.add_argument(
        "--config",
        default="raspberry_pi/safety_control/config.safety_control.json",
    )
    parser.add_argument("--input-mode", choices=("scenario", "camera"), default="scenario")
    parser.add_argument("--camera-log-file", default="data/logs/camera_ai_log.csv")
    parser.add_argument("--output", default="data/logs/feeding_decision_log.csv")
    parser.add_argument("--mock-contact", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--mock-impedance-kohm", type=float, default=92.4)
    parser.add_argument("--honey-amount-percent", type=int)
    parser.add_argument(
        "--system-safe",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--emergency-stop", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--max-iterations", type=int)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = SafetyConfig.load(Path(args.config))
    state_machine = SafetyStateMachine(config)
    if args.input_mode == "camera":
        honey_amount_percent = (
            config.default_honey_amount_percent
            if args.honey_amount_percent is None
            else args.honey_amount_percent
        )
        input_source = CameraCsvInput(
            Path(args.camera_log_file),
            config,
            mock_contact=args.mock_contact,
            mock_impedance_kohm=args.mock_impedance_kohm,
            honey_amount_percent=honey_amount_percent,
            system_safe=args.system_safe,
            emergency_stop=args.emergency_stop,
        )
    else:
        input_source = ScenarioInput(config)

    output_path = Path(args.output)
    iteration = 0
    try:
        while True:
            inputs = input_source.read()
            now_ms = int(time.monotonic() * 1000)
            decision = state_machine.update(inputs, now_ms)
            record = build_record(inputs, decision, input_mode=args.input_mode)
            append_csv(output_path, record)
            print(json.dumps(record, ensure_ascii=False, separators=(",", ":")), flush=True)
            iteration += 1
            if args.once or (
                args.max_iterations is not None and iteration >= args.max_iterations
            ):
                break
            time.sleep(config.log_interval_ms / 1000.0)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "timestamp": now_iso8601(),
                    "state": State.ERROR_SAFE.value,
                    "release_state": "RELEASE_OFF",
                    "servo_command": "HOLD",
                    "event": "PROCESS_EXCEPTION",
                    "error_message": str(exc),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
