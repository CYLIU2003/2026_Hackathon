import argparse
import csv
import json
import sys
import time
from pathlib import Path

import serial


CSV_FIELDNAMES = [
    "timestamp",
    "state",
    "previous_state",
    "event",
    "bear_detected",
    "paw_contact",
    "contact_confirmed",
    "raw_contact_value",
    "honey_amount_percent",
    "honey_enough",
    "system_safe",
    "emergency_stop",
    "release_allowed",
    "release_state",
    "error_code",
    "error_message",
]

REQUIRED_FIELDS = [
    "timestamp",
    "state",
    "event",
    "bear_detected",
    "paw_contact",
    "honey_amount_percent",
    "system_safe",
    "emergency_stop",
    "release_state",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Arduino Uno Q JSON Lines serial logger")
    parser.add_argument("--serial-port", default="/dev/ttyACM0")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--log-dir", default="data/logs")
    return parser.parse_args()


def ensure_log_file(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return log_dir / f"log_{timestamp}.csv"


def validate_message(message: dict) -> list[str]:
    missing = [field for field in REQUIRED_FIELDS if field not in message]
    return missing


def build_csv_row(message: dict) -> dict:
    row = {}
    for field in CSV_FIELDNAMES:
        value = message.get(field, "")
        if value is None:
            value = ""
        row[field] = value
    return row


def log_status(counter: int, invalid: int, row: dict) -> None:
    print(
        f"[{counter}] state={row.get('state')} event={row.get('event')} "
        f"release={row.get('release_state')} bear={row.get('bear_detected')} "
        f"contact={row.get('paw_contact')} honey={row.get('honey_amount_percent')} "
        f"invalid={invalid}",
        flush=True,
    )


def main() -> int:
    args = parse_args()
    log_dir = Path(args.log_dir)
    log_path = ensure_log_file(log_dir)

    try:
        serial_port = serial.Serial(args.serial_port, args.baudrate, timeout=1)
    except serial.SerialException as exc:
        print(f"Failed to open serial port: {exc}", file=sys.stderr)
        return 1

    with log_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        csv_file.flush()

        received = 0
        invalid = 0

        try:
            while True:
                line_bytes = serial_port.readline()
                if not line_bytes:
                    continue

                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    invalid += 1
                    print(f"Invalid JSON: {line}", file=sys.stderr)
                    continue

                if not isinstance(message, dict):
                    invalid += 1
                    print(f"Invalid message type: {type(message)}", file=sys.stderr)
                    continue

                missing = validate_message(message)
                if missing:
                    invalid += 1
                    print(f"Missing fields: {missing}", file=sys.stderr)
                    continue

                row = build_csv_row(message)
                writer.writerow(row)
                csv_file.flush()

                received += 1
                log_status(received, invalid, row)
        except KeyboardInterrupt:
            print("Logger stopped.", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
