from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CSV_COLUMNS = [
    "timestamp",
    "source",
    "camera_device",
    "ai_camera_ok",
    "ai_model_ok",
    "ai_bear_detected",
    "ai_bear_confidence",
    "ai_bear_box_area_ratio",
    "ai_bear_approaching",
    "event",
    "inference_time_ms",
]


def now_iso8601() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True)
class AiState:
    camera_device: str
    ai_camera_ok: bool
    ai_model_ok: bool
    ai_bear_detected: bool
    ai_bear_confidence: Optional[float]
    ai_bear_box_area_ratio: Optional[float]
    ai_bear_approaching: bool
    event: str
    inference_time_ms: Optional[float]
    timestamp: Optional[str] = None
    source: str = "camera_ai"

    def to_record(self) -> dict:
        return {
            "timestamp": self.timestamp or now_iso8601(),
            "source": self.source,
            "camera_device": self.camera_device,
            "ai_camera_ok": self.ai_camera_ok,
            "ai_model_ok": self.ai_model_ok,
            "ai_bear_detected": self.ai_bear_detected,
            "ai_bear_confidence": self.ai_bear_confidence,
            "ai_bear_box_area_ratio": self.ai_bear_box_area_ratio,
            "ai_bear_approaching": self.ai_bear_approaching,
            "event": self.event,
            "inference_time_ms": self.inference_time_ms,
        }


class AiStatePublisher:
    def __init__(
        self,
        *,
        jsonl_stdout: bool = True,
        save_csv: bool = True,
        csv_path: Optional[Path] = None,
    ):
        self.jsonl_stdout = jsonl_stdout
        self.save_csv = save_csv
        self.csv_path = csv_path

    def publish(self, state: AiState) -> dict:
        record = state.to_record()
        if self.jsonl_stdout:
            print(json.dumps(record, separators=(",", ":")), flush=True)
        if self.save_csv and self.csv_path is not None:
            self._append_csv(record)
        return record

    def _append_csv(self, record: dict) -> None:
        assert self.csv_path is not None
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not self.csv_path.exists()
        with self.csv_path.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
            if write_header:
                writer.writeheader()
            writer.writerow({column: record.get(column, "") for column in CSV_COLUMNS})

