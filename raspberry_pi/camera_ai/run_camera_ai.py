from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

try:
    from .ai_state_publisher import AiState, AiStatePublisher
    from .approach_logic import ApproachDetectionConfig, ApproachLogic
    from .bear_detector import YoloBearDetector
    from .camera_capture import (
        OpenCvCameraDriver,
        camera_driver_from_config,
    )
except ImportError:
    from ai_state_publisher import AiState, AiStatePublisher
    from approach_logic import ApproachDetectionConfig, ApproachLogic
    from bear_detector import YoloBearDetector
    from camera_capture import (
        OpenCvCameraDriver,
        camera_driver_from_config,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run camera AI bear detection.")
    parser.add_argument("--config", default="raspberry_pi/camera_ai/config.camera_ai.yaml")
    parser.add_argument(
        "--camera",
        type=int,
        default=None,
        help="Explicit OpenCV camera index override. Default uses /dev/video0.",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Linux video device path override. Default and target hardware path is /dev/video0.",
    )
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
    parser.add_argument(
        "--save-debug-frames",
        action="store_true",
        help="Save the latest annotated camera frame for the remote dashboard.",
    )
    parser.add_argument(
        "--no-debug-frames",
        action="store_true",
        help="Disable annotated camera frame output even if enabled in config.",
    )
    parser.add_argument(
        "--no-inference",
        action="store_true",
        help=(
            "Skip YOLO inference and run in camera-only fail-safe mode. "
            "Outputs ai_model_ok=false and ai_bear_detected=false while still "
            "capturing frames and writing CSV/JSONL/terminal status. Useful when "
            "the NCNN native library segfaults on the current platform."
        ),
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


def resolve_model_path(
    inference_config: dict,
    model_override: str | None = None,
) -> Path:
    if model_override:
        return repo_path(model_override)

    primary_model_path = inference_config.get(
        "model_path", "models/yolo_bear_ncnn_model"
    )
    candidate_paths = [primary_model_path]
    candidate_paths.extend(inference_config.get("fallback_model_paths", []))
    resolved_candidates = [repo_path(candidate_path) for candidate_path in candidate_paths]
    for candidate_path in resolved_candidates:
        if candidate_path.exists():
            return candidate_path
    return resolved_candidates[0]


def resolve_model_candidates(
    inference_config: dict,
    model_override: str | None = None,
) -> list[Path]:
    if model_override:
        return [repo_path(model_override)]

    primary_model_path = inference_config.get(
        "model_path", "models/yolo_bear_ncnn_model"
    )
    candidate_paths = [primary_model_path]
    candidate_paths.extend(inference_config.get("fallback_model_paths", []))
    resolved_candidates = [
        repo_path(candidate_path) for candidate_path in candidate_paths
    ]
    existing_candidates = [
        candidate_path for candidate_path in resolved_candidates if candidate_path.exists()
    ]
    if existing_candidates:
        # Prefer ONNX files over NCNN directories on platforms where the NCNN
        # native runtime segfaults. This lets a single dropped-in yolo_bear.onnx
        # switch the system to the ONNX Runtime backend automatically.
        def _priority(path: Path) -> int:
            if path.suffix.lower() == ".onnx":
                return 0
            if path.is_dir() and any(path.glob("*.ncnn.param")):
                return 1
            return 2

        return sorted(existing_candidates, key=_priority)
    return [resolved_candidates[0]]


def load_detector_from_candidates(
    inference_config: dict,
    model_override: str | None = None,
) -> tuple[YoloBearDetector, Path]:
    load_errors: list[str] = []
    for model_path in resolve_model_candidates(inference_config, model_override):
        try:
            return (
                YoloBearDetector(
                    model_path,
                    input_size=int(inference_config.get("input_size", 256)),
                    confidence_floor=float(
                        inference_config.get("confidence_floor", 0.05)
                    ),
                    device=inference_config.get("device", "cpu"),
                    class_ids=inference_config.get("class_ids", []),
                ),
                model_path,
            )
        except Exception as exc:
            load_errors.append(f"{model_path}: {exc}")

    raise RuntimeError(
        "failed to load any configured YOLO model. "
        + " | ".join(load_errors)
    )


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
    return (
        f"{record.get('timestamp', '-')} "
        f"event={record.get('event', '-')} "
        f"camera={camera_status} "
        f"model={model_status} "
        f"bear={bear_status} "
        f"conf={format_optional_float(record.get('ai_bear_confidence'))} "
        f"area={format_optional_percent(record.get('ai_bear_box_area_ratio'))} "
        f"infer_ms={format_optional_float(record.get('inference_time_ms'), digits=1)} "
        f"device={record.get('camera_device', '-')}"
    )


def print_terminal_status(record: dict) -> None:
    print(format_terminal_status(record), file=sys.stderr, flush=True)


def debug_frame_enabled(output_config: dict, args: argparse.Namespace) -> bool:
    if args.no_debug_frames:
        return False
    return args.save_debug_frames or bool(output_config.get("save_debug_frames", False))


def draw_status_panel(cv2, frame, record: dict) -> None:
    event = str(record.get("event") or "-")
    event_label = {
        "AI_NO_BEAR": "NO_BEAR",
        "AI_BEAR_DETECTED": "BEAR",
    }.get(event, event)
    confidence = format_optional_float(record.get("ai_bear_confidence"))
    inference_ms = format_optional_float(record.get("inference_time_ms"), digits=1)
    line = f"{event_label} conf={confidence} infer={inference_ms}ms"
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 34), (0, 0, 0), thickness=-1)
    cv2.putText(
        frame,
        line,
        (8, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )


def draw_detections(cv2, frame, detections: list[dict]) -> None:
    for detection in detections:
        bbox = detection.get("bbox_xyxy")
        if not bbox or len(bbox) != 4:
            continue
        x1, y1, x2, y2 = [int(round(float(value))) for value in bbox]
        class_name = str(detection.get("class_name", "object"))
        confidence = format_optional_float(detection.get("confidence"))
        area = format_optional_percent(detection.get("box_area_ratio"))
        label = f"{class_name} {confidence} {area}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 180, 255), thickness=2)
        label_y = max(16, y1 - 8)
        cv2.putText(
            frame,
            label,
            (x1, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 180, 255),
            1,
            cv2.LINE_AA,
        )


def filter_display_detections(
    detections: list[dict],
    approach_config: ApproachDetectionConfig,
) -> list[dict]:
    target_classes = {class_name.lower() for class_name in approach_config.target_classes}
    return [
        detection
        for detection in detections
        if str(detection.get("class_name", "")).lower() in target_classes
        and float(detection.get("confidence", 0.0))
        >= approach_config.confidence_threshold
    ]


def prepare_display_frame(cv2, frame):
    display_frame = frame.copy()
    gray_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2GRAY)
    brightness_mean = float(gray_frame.mean())
    if brightness_mean > 170.0:
        display_frame = cv2.convertScaleAbs(display_frame, alpha=0.65, beta=-30)
    elif brightness_mean < 35.0:
        display_frame = cv2.convertScaleAbs(display_frame, alpha=1.8, beta=20)

    return display_frame


def build_dark_frame_notice(cv2, frame, record: dict):
    height, width = frame.shape[:2]
    notice_frame = frame.copy()
    notice_frame[:] = (44, 44, 44)
    cv2.rectangle(notice_frame, (0, 0), (width, 42), (0, 0, 0), thickness=-1)
    cv2.putText(
        notice_frame,
        "CAMERA_DARK",
        (10, 27),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        notice_frame,
        "camera is returning dark frames",
        (10, max(78, height // 2 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (230, 230, 230),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        notice_frame,
        "reopening camera safely",
        (10, max(108, height // 2 + 22)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (230, 230, 230),
        1,
        cv2.LINE_AA,
    )
    return notice_frame


def save_debug_frame(
    frame,
    detections: list[dict],
    record: dict,
    *,
    debug_frame_dir: Path,
    latest_frame_name: str,
) -> Path:
    import cv2

    debug_frame_dir.mkdir(parents=True, exist_ok=True)
    latest_frame_path = debug_frame_dir / latest_frame_name
    temporary_frame_path = latest_frame_path.with_suffix(".tmp.jpg")
    if record.get("event") == "AI_CAMERA_DARK_FRAME":
        annotated_frame = build_dark_frame_notice(cv2, frame, record)
    else:
        annotated_frame = prepare_display_frame(cv2, frame)
        draw_detections(cv2, annotated_frame, detections)
        draw_status_panel(cv2, annotated_frame, record)
    if not cv2.imwrite(str(temporary_frame_path), annotated_frame):
        raise RuntimeError(f"failed to write debug frame: {temporary_frame_path}")
    temporary_frame_path.replace(latest_frame_path)
    return latest_frame_path


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


def run_detection(detector: YoloBearDetector, frame) -> tuple[list[dict], float]:
    started_at = time.perf_counter()
    detections = detector.detect(frame)
    inference_time_ms = (time.perf_counter() - started_at) * 1000.0
    return detections, inference_time_ms


def camera_failure_is_transient(
    *,
    last_camera_ok_at: float | None,
    now_monotonic: float,
    grace_sec: float,
) -> bool:
    if last_camera_ok_at is None:
        return False
    return now_monotonic - last_camera_ok_at <= max(0.0, grace_sec)


def run_camera_only_failsafe_loop(
    *,
    args,
    publisher: AiStatePublisher,
    driver: OpenCvCameraDriver,
    save_frames: bool,
    debug_frame_dir: Path,
    latest_frame_name: str,
    debug_frame_interval_sec: float,
    output_config: dict,
    camera_error_grace_sec: float,
    initial_camera_ok: bool,
) -> int:
    """Camera-only fail-safe loop used when inference is disabled or unsafe.

    Emits ai_model_ok=false and ai_bear_detected=false on every cycle,
    keeps writing the latest camera frame, and never touches the YOLO model.
    This keeps the dashboard visually live while remaining in safe HOLD.
    """
    failsafe_state = AiState(
        camera_device=driver.camera_device,
        ai_camera_ok=True,
        ai_model_ok=False,
        ai_bear_detected=False,
        ai_bear_confidence=None,
        ai_bear_box_area_ratio=None,
        event="AI_INFERENCE_DISABLED",
        inference_time_ms=None,
    )
    failsafe_record = failsafe_state.to_record()
    last_record = failsafe_record
    last_debug_frame_saved_at = 0.0
    iteration_count = 0
    last_camera_ok_at = time.monotonic() if initial_camera_ok else None
    try:
        while True:
            read_result = driver.read_frame()
            if not read_result.ok or read_result.frame is None:
                now_monotonic = time.monotonic()
                if (
                    not args.once
                    and camera_failure_is_transient(
                        last_camera_ok_at=last_camera_ok_at,
                        now_monotonic=now_monotonic,
                        grace_sec=camera_error_grace_sec,
                    )
                ):
                    time.sleep(0.05)
                    continue
                last_record = publish_state(
                    publisher,
                    build_fail_safe_state(
                        camera_device=read_result.camera_device,
                        ai_camera_ok=False,
                        ai_model_ok=False,
                        event=read_result.event,
                    ),
                    terminal_status=args.terminal_status,
                )
                if save_frames and read_result.frame is not None:
                    save_debug_frame(
                        read_result.frame,
                        [],
                        last_record,
                        debug_frame_dir=debug_frame_dir,
                        latest_frame_name=latest_frame_name,
                    )
                if args.once:
                    return 1
                iteration_count += 1
                if (
                    args.max_iterations is not None
                    and iteration_count >= args.max_iterations
                ):
                    break
                time.sleep(0.05)
                continue

            frame = read_result.frame

            now_monotonic = time.monotonic()
            last_camera_ok_at = now_monotonic
            should_save_debug_frame = (
                save_frames
                and now_monotonic - last_debug_frame_saved_at >= debug_frame_interval_sec
            )
            if should_save_debug_frame:
                save_debug_frame(
                    frame,
                    [],
                    last_record,
                    debug_frame_dir=debug_frame_dir,
                    latest_frame_name=latest_frame_name,
                )
                last_debug_frame_saved_at = now_monotonic

            last_record = publish_state(
                publisher,
                AiState(
                    camera_device=read_result.camera_device,
                    ai_camera_ok=True,
                    ai_model_ok=False,
                    ai_bear_detected=False,
                    ai_bear_confidence=None,
                    ai_bear_box_area_ratio=None,
                    event="AI_INFERENCE_DISABLED",
                    inference_time_ms=None,
                ),
                terminal_status=args.terminal_status,
            )
            iteration_count += 1

            if use_display_active(output_config):
                import cv2

                cv2.imshow("camera_ai", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if args.once or (
                args.max_iterations is not None
                and iteration_count >= args.max_iterations
            ):
                break
            time.sleep(0.05)
    except KeyboardInterrupt:
        return 0
    finally:
        driver.close()
        if use_display_active(output_config):
            import cv2

            cv2.destroyAllWindows()
    return 0


def use_display_active(output_config: dict) -> bool:
    return bool(output_config.get("use_display", False))


def main() -> int:
    args = build_parser().parse_args()
    try:
        config = load_config(config_path(args.config))
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    output_config = config.get("output", {})
    camera_config = config.get("camera", {})
    fail_safe_config = config.get("fail_safe", {})
    save_frames = debug_frame_enabled(output_config, args)
    debug_frame_dir = repo_path(output_config.get("debug_frame_dir", "data/debug_frames"))
    latest_frame_name = str(
        output_config.get("latest_debug_frame", "latest_camera_ai.jpg")
    )
    debug_frame_interval_sec = float(output_config.get("debug_frame_interval_sec", 1.0))
    publisher = AiStatePublisher(
        jsonl_stdout=bool(output_config.get("jsonl_stdout", True)) and not args.no_jsonl,
        save_csv=bool(output_config.get("save_csv", True)),
        csv_path=repo_path(output_config.get("csv_path", "data/logs/camera_ai_log.csv")),
    )

    try:
        import cv2
    except ImportError:
        print("ERROR: opencv-python is not installed.")
        return 1

    driver = camera_driver_from_config(
        cv2,
        camera_config,
        fail_safe_config=fail_safe_config,
        camera_override=args.camera,
        device_override=args.device,
    )
    startup_read = driver.read_frame()
    camera_device = startup_read.camera_device
    if not startup_read.ok:
        publish_state(
            publisher,
            build_fail_safe_state(
                camera_device=camera_device,
                ai_camera_ok=False,
                ai_model_ok=False,
                event=startup_read.event,
            ),
            terminal_status=args.terminal_status,
        )
        if args.once:
            driver.close()
            return 1

    if save_frames and startup_read.ok and startup_read.frame is not None:
        save_debug_frame(
            startup_read.frame,
            [],
            AiState(
                camera_device=camera_device,
                ai_camera_ok=True,
                ai_model_ok=False,
                ai_bear_detected=False,
                ai_bear_confidence=None,
                ai_bear_box_area_ratio=None,
                event="AI_MODEL_LOADING",
                inference_time_ms=None,
            ).to_record(),
            debug_frame_dir=debug_frame_dir,
            latest_frame_name=latest_frame_name,
        )

    if args.no_inference:
        if args.terminal_status:
            print(
                "inference=disabled (camera-only fail-safe mode)",
                file=sys.stderr,
                flush=True,
            )
        return run_camera_only_failsafe_loop(
            args=args,
            publisher=publisher,
            driver=driver,
            save_frames=save_frames,
            debug_frame_dir=debug_frame_dir,
            latest_frame_name=latest_frame_name,
            debug_frame_interval_sec=debug_frame_interval_sec,
            output_config=output_config,
            camera_error_grace_sec=float(
                fail_safe_config.get("camera_error_grace_sec", 2.0)
            ),
            initial_camera_ok=startup_read.ok,
        )

    inference_config = config.get("inference", {})
    try:
        detector, model_path = load_detector_from_candidates(
            inference_config, args.model
        )
        if args.terminal_status:
            print(f"selected_model={model_path}", file=sys.stderr, flush=True)
    except Exception as exc:
        driver.close()
        if args.terminal_status:
            print(f"model_load_error={exc}", file=sys.stderr, flush=True)
        publish_state(
            publisher,
            build_fail_safe_state(
                camera_device=camera_device,
                ai_camera_ok=startup_read.ok,
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
    last_detections: list[dict] = []
    last_record = AiState(
        camera_device=camera_device,
        ai_camera_ok=True,
        ai_model_ok=True,
        ai_bear_detected=False,
        ai_bear_confidence=None,
        ai_bear_box_area_ratio=None,
        event="AI_WAITING_FOR_INFERENCE",
        inference_time_ms=None,
    ).to_record()
    last_debug_frame_saved_at = 0.0
    last_inference_completed_at = -inference_interval_sec
    inference_future: Future | None = None
    camera_error_grace_sec = float(
        fail_safe_config.get("camera_error_grace_sec", 2.0)
    )
    last_camera_ok_at = time.monotonic() if startup_read.ok else None

    executor = ThreadPoolExecutor(max_workers=1)
    try:
        while True:
            read_result = driver.read_frame()
            camera_device = read_result.camera_device
            if not read_result.ok or read_result.frame is None:
                now_monotonic = time.monotonic()
                if (
                    not args.once
                    and camera_failure_is_transient(
                        last_camera_ok_at=last_camera_ok_at,
                        now_monotonic=now_monotonic,
                        grace_sec=camera_error_grace_sec,
                    )
                ):
                    time.sleep(0.05)
                    continue
                failure_record = publish_state(
                    publisher,
                    build_fail_safe_state(
                        camera_device=camera_device,
                        ai_camera_ok=False,
                        ai_model_ok=True,
                        event=read_result.event,
                    ),
                    terminal_status=args.terminal_status,
                )
                if save_frames and read_result.frame is not None:
                    save_debug_frame(
                        read_result.frame,
                        [],
                        failure_record,
                        debug_frame_dir=debug_frame_dir,
                        latest_frame_name=latest_frame_name,
                    )
                    last_debug_frame_saved_at = time.monotonic()
                if args.once:
                    return 1
                time.sleep(0.05)
                continue

            frame = read_result.frame

            now_monotonic = time.monotonic()
            last_camera_ok_at = now_monotonic
            completed_inference = False
            if inference_future is not None and inference_future.done():
                try:
                    detections, inference_time_ms = inference_future.result()
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

                decision = approach_logic.update(detections)
                last_record = publish_state(
                    publisher,
                    AiState(
                        camera_device=camera_device,
                        ai_camera_ok=True,
                        ai_model_ok=True,
                        ai_bear_detected=decision.ai_bear_detected,
                        ai_bear_confidence=decision.ai_bear_confidence,
                        ai_bear_box_area_ratio=decision.ai_bear_box_area_ratio,
                        event=decision.event,
                        inference_time_ms=round(inference_time_ms, 2),
                    ),
                    terminal_status=args.terminal_status,
                )
                last_detections = filter_display_detections(
                    detections,
                    approach_logic.config,
                )
                iteration_count += 1
                completed_inference = True
                last_inference_completed_at = now_monotonic
                inference_future = None

            should_start_inference = (
                inference_future is None
                and now_monotonic - last_inference_completed_at >= inference_interval_sec
            )
            if should_start_inference:
                inference_future = executor.submit(run_detection, detector, frame.copy())

            should_save_debug_frame = (
                save_frames
                and now_monotonic - last_debug_frame_saved_at >= debug_frame_interval_sec
            )
            if should_save_debug_frame or (save_frames and completed_inference):
                save_debug_frame(
                    frame,
                    last_detections,
                    last_record,
                    debug_frame_dir=debug_frame_dir,
                    latest_frame_name=latest_frame_name,
                )
                last_debug_frame_saved_at = now_monotonic

            if use_display:
                cv2.imshow("camera_ai", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if completed_inference and (args.once or (
                args.max_iterations is not None
                and iteration_count >= args.max_iterations
            )):
                break
            time.sleep(0.01)
    except KeyboardInterrupt:
        return 0
    except Exception:
        publish_state(
            publisher,
            build_fail_safe_state(
                camera_device=driver.camera_device,
                ai_camera_ok=True,
                ai_model_ok=True,
                event="AI_RUNTIME_ERROR",
            ),
            terminal_status=args.terminal_status,
        )
        return 1
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
        driver.close()
        if use_display:
            cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
