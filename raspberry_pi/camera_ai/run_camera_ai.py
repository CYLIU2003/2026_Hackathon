from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

from ai_state_publisher import AiState, AiStatePublisher
from approach_logic import ApproachDetectionConfig, ApproachLogic
from bear_detector import YoloBearDetector

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run camera AI bear approach detection.")
    parser.add_argument("--config", default="raspberry_pi/camera_ai/config.camera_ai.yaml")
    parser.add_argument("--camera", type=int, default=None, help="OpenCV camera index override.")
    parser.add_argument("--device", default=None, help="Linux video device path override.")
    parser.add_argument("--model", default=None, help="YOLO model path override.")
    parser.add_argument("--once", action="store_true", help="Run one inference cycle and exit.")
    parser.add_argument("--max-iterations", type=int, default=None)
    parser.add_argument(
        "--terminal-status",
        action="store_true",
        help="Print compact human-readable status lines to stderr for SSH/CUI use.",
    )
    parser.add_argument(
        "--no-jsonl",
        action="store_true",
        help="Disable JSON Lines stdout. Useful with --terminal-status for human-only CUI use.",
    )
    return parser


def load_config(config_path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is not installed. Install raspberry_pi/camera_ai/requirements.txt."
        ) from exc

    with config_path.open("r", encoding="utf-8") as config_file:
        loaded = yaml.safe_load(config_file) or {}
    return loaded


def repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else REPO_ROOT / path


def config_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    script_relative_path = SCRIPT_DIR / path
    if script_relative_path.exists():
        return script_relative_path
    return REPO_ROOT / path


def open_camera(camera_config: dict, camera_override: int | None, device_override: str | None):
    import cv2

    if device_override:
        camera_source: Any = device_override
    elif camera_override is not None:
        camera_source = camera_override
    elif camera_config.get("device"):
        camera_source = str(camera_config["device"])
    else:
        camera_source = int(camera_config.get("index", 0))

    backend = cv2.CAP_V4L2 if os.name == "posix" else cv2.CAP_ANY
    capture = cv2.VideoCapture(camera_source, backend)
    fourcc = str(camera_config.get("fourcc", "MJPG"))
    if fourcc:
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc[:4]))
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(camera_config.get("width", 640)))
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(camera_config.get("height", 480)))
    capture.set(cv2.CAP_PROP_FPS, int(camera_config.get("fps", 15)))
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return capture, str(camera_source)


def read_frame_with_retries(capture, *, retries: int = 1, retry_delay_sec: float = 0.1):
    for _ in range(max(1, retries)):
        ok, frame = capture.read()
        if ok and frame is not None:
            return ok, frame
        time.sleep(max(0.0, retry_delay_sec))
    return False, None


def build_fail_safe_state(
    *,
    camera_device: str,
    ai_camera_ok: bool,
    ai_model_ok: bool,
    event: str,
) -> AiState:
    return AiState(
        camera_device=camera_device,
        ai_camera_ok=ai_camera_ok,
        ai_model_ok=ai_model_ok,
        ai_bear_detected=False,
        ai_bear_confidence=None,
        ai_bear_box_area_ratio=None,
        ai_bear_approaching=False,
        event=event,
        inference_time_ms=None,
    )


def format_optional_float(value: Any, *, digits: int = 2) -> str:
    if value is None or value == "":
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def format_optional_percent(value: Any, *, digits: int = 1) -> str:
    if value is None or value == "":
        return "-"
    try:
        return f"{float(value) * 100.0:.{digits}f}%"
    except (TypeError, ValueError):
        return "-"


def format_terminal_status(record: dict) -> str:
    camera_status = "ok" if record.get("ai_camera_ok") else "error"
    model_status = "ok" if record.get("ai_model_ok") else "error"
    bear_status = "yes" if record.get("ai_bear_detected") else "no"
    approaching_status = "yes" if record.get("ai_bear_approaching") else "no"
    return (
        f"{record.get('timestamp', '-')} "
        f"event={record.get('event', '-')} "
        f"camera={camera_status} "
        f"model={model_status} "
        f"bear={bear_status} "
        f"approaching={approaching_status} "
        f"conf={format_optional_float(record.get('ai_bear_confidence'))} "
        f"area={format_optional_percent(record.get('ai_bear_box_area_ratio'))} "
        f"infer_ms={format_optional_float(record.get('inference_time_ms'), digits=1)} "
        f"device={record.get('camera_device', '-')}"
    )


def print_terminal_status(record: dict) -> None:
    print(format_terminal_status(record), file=sys.stderr, flush=True)


def publish_state(
    publisher: AiStatePublisher,
    state: AiState,
    *,
    terminal_status: bool,
) -> dict:
    record = publisher.publish(state)
    if terminal_status:
        print_terminal_status(record)
    return record


def main() -> int:
    args = build_parser().parse_args()
    try:
        config = load_config(config_path(args.config))
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    output_config = config.get("output", {})
    publisher = AiStatePublisher(
        jsonl_stdout=bool(output_config.get("jsonl_stdout", True)) and not args.no_jsonl,
        save_csv=bool(output_config.get("save_csv", True)),
        csv_path=repo_path(output_config.get("csv_path", "data/logs/camera_ai_log.csv")),
    )

    try:
        capture, camera_device = open_camera(
            config.get("camera", {}),
            args.camera,
            args.device,
        )
    except Exception:
        camera_device = args.device or str(args.camera or config.get("camera", {}).get("device", "0"))
        publish_state(
            publisher,
            build_fail_safe_state(
                camera_device=camera_device,
                ai_camera_ok=False,
                ai_model_ok=False,
                event="AI_CAMERA_OPEN_ERROR",
            ),
            terminal_status=args.terminal_status,
        )
        return 1

    if not capture.isOpened():
        publish_state(
            publisher,
            build_fail_safe_state(
                camera_device=camera_device,
                ai_camera_ok=False,
                ai_model_ok=False,
                event="AI_CAMERA_OPEN_ERROR",
            ),
            terminal_status=args.terminal_status,
        )
        return 1

    inference_config = config.get("inference", {})
    model_path = args.model or inference_config.get("model_path", "models/yolo_bear.pt")
    try:
        detector = YoloBearDetector(
            repo_path(model_path),
            input_size=int(inference_config.get("input_size", 320)),
        )
    except Exception:
        capture.release()
        publish_state(
            publisher,
            build_fail_safe_state(
                camera_device=camera_device,
                ai_camera_ok=True,
                ai_model_ok=False,
                event="AI_MODEL_LOAD_ERROR",
            ),
            terminal_status=args.terminal_status,
        )
        return 1

    approach_logic = ApproachLogic(
        ApproachDetectionConfig.from_mapping(config.get("approach_detection", {}))
    )
    inference_interval_sec = float(inference_config.get("inference_interval_sec", 0.5))
    use_display = bool(inference_config.get("use_display", False))
    iteration_count = 0

    try:
        while True:
            ok, frame = read_frame_with_retries(capture)
            if not ok or frame is None:
                publish_state(
                    publisher,
                    build_fail_safe_state(
                        camera_device=camera_device,
                        ai_camera_ok=False,
                        ai_model_ok=True,
                        event="AI_CAMERA_FRAME_ERROR",
                    ),
                    terminal_status=args.terminal_status,
                )
                return 1

            started_at = time.perf_counter()
            detections = detector.detect(frame)
            inference_time_ms = (time.perf_counter() - started_at) * 1000.0
            decision = approach_logic.update(detections)

            publish_state(
                publisher,
                AiState(
                    camera_device=camera_device,
                    ai_camera_ok=True,
                    ai_model_ok=True,
                    ai_bear_detected=decision.ai_bear_detected,
                    ai_bear_confidence=decision.ai_bear_confidence,
                    ai_bear_box_area_ratio=decision.ai_bear_box_area_ratio,
                    ai_bear_approaching=decision.ai_bear_approaching,
                    event=decision.event,
                    inference_time_ms=round(inference_time_ms, 2),
                ),
                terminal_status=args.terminal_status,
            )

            if use_display:
                import cv2

                cv2.imshow("camera_ai", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            iteration_count += 1
            if args.once or (
                args.max_iterations is not None
                and iteration_count >= args.max_iterations
            ):
                break
            time.sleep(inference_interval_sec)
    except KeyboardInterrupt:
        return 0
    except Exception:
        publish_state(
            publisher,
            build_fail_safe_state(
                camera_device=camera_device,
                ai_camera_ok=True,
                ai_model_ok=True,
                event="AI_RUNTIME_ERROR",
            ),
            terminal_status=args.terminal_status,
        )
        return 1
    finally:
        capture.release()
        if use_display:
            import cv2

            cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
