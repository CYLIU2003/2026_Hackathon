#!/usr/bin/env python3
"""
Fake Camera AI JSON Lines generator.

This does not talk to Arduino. It only emits JSON Lines with fields compatible
with the Camera AI side of the A1 prototype. Use it when Raspberry Pi, USB
camera, or YOLO model is unavailable.

Example:
  python3 raspberry_pi/test_tools/fake_camera_ai_jsonl.py --loop
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


def now_jst_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def make_record(i: int, detected: bool, approaching: bool) -> dict:
    return {
        "timestamp": now_jst_iso(),
        "source": "fake_camera_ai",
        "camera_device": "FAKE_CAMERA",
        "ai_camera_ok": True,
        "ai_model_ok": True,
        "ai_bear_detected": detected,
        "ai_bear_confidence": 0.90 if detected else 0.0,
        "ai_bear_box_area_ratio": 0.20 if detected else 0.0,
        "ai_bear_approaching": approaching,
        "event": "AI_BEAR_APPROACHING" if approaching else "AI_IDLE",
        "inference_time_ms": 1.0,
        "fake_step": i,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval-sec", type=float, default=1.0)
    parser.add_argument("--bear-every", type=int, default=3, help="emit bear detected every N records")
    parser.add_argument("--max-iterations", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    i = 0

    while True:
        i += 1
        detected = (i % args.bear_every) != 1
        approaching = detected
        print(json.dumps(make_record(i, detected, approaching), ensure_ascii=False), flush=True)
        time.sleep(args.interval_sec)

        if not args.loop and i >= args.max_iterations:
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
