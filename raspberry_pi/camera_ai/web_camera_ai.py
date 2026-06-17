from __future__ import annotations

import argparse
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from .ai_state_publisher import AiState, AiStatePublisher
    from .approach_logic import ApproachDetectionConfig, ApproachLogic
    from .bear_detector import YoloBearDetector
    from .camera_capture import (
        DEFAULT_CAMERA_DEVICE,
        fallback_profiles,
        open_camera_with_fallbacks,
        read_frame_with_retries,
        resolve_camera_source,
    )
    from .run_camera_ai import (
        build_fail_safe_state,
        config_path,
        load_config,
        repo_path,
        resolve_model_path,
    )
except ImportError:
    from ai_state_publisher import AiState, AiStatePublisher
    from approach_logic import ApproachDetectionConfig, ApproachLogic
    from bear_detector import YoloBearDetector
    from camera_capture import (
        DEFAULT_CAMERA_DEVICE,
        fallback_profiles,
        open_camera_with_fallbacks,
        read_frame_with_retries,
        resolve_camera_source,
    )
    from run_camera_ai import (
        build_fail_safe_state,
        config_path,
        load_config,
        repo_path,
        resolve_model_path,
    )

HTML_TEMPLATE = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>A1 Camera AI Viewer</title>
    <style>
      body { margin: 0; font-family: Arial, sans-serif; background: #111; color: #f5f5f5; }
      main { max-width: 980px; margin: 0 auto; padding: 16px; }
      img { width: 100%; height: auto; background: #222; border: 1px solid #444; }
      .status { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px; margin: 12px 0; }
      .item { background: #1e1e1e; border: 1px solid #333; padding: 8px; }
      .label { color: #aaa; font-size: 12px; }
      .value { font-size: 18px; font-weight: bold; }
      .safe { color: #8ee58e; }
      .warn { color: #ffd166; }
      .bad { color: #ff7b7b; }
      code { color: #c9e4ff; }
    </style>
  </head>
  <body>
    <main>
      <h1>A1 Camera AI Viewer</h1>
      <img src="/video.mjpg" alt="camera AI stream" />
      <div class="status">
        <div class="item"><div class="label">event</div><div id="event" class="value">-</div></div>
        <div class="item"><div class="label">bear</div><div id="bear" class="value">-</div></div>
        <div class="item"><div class="label">approaching</div><div id="approaching" class="value">-</div></div>
        <div class="item"><div class="label">confidence</div><div id="confidence" class="value">-</div></div>
        <div class="item"><div class="label">area</div><div id="area" class="value">-</div></div>
        <div class="item"><div class="label">inference ms</div><div id="inference" class="value">-</div></div>
      </div>
      <p>This camera AI is a support signal only. It does not command honey release.</p>
      <p>Status JSON: <code>/status.json</code></p>
    </main>
    <script>
      async function refreshStatus() {
        const response = await fetch('/status.json', {cache: 'no-store'});
        const data = await response.json();
        function text(id, value) { document.getElementById(id).textContent = value ?? '-'; }
        text('event', data.event);
        text('bear', data.ai_bear_detected ? 'yes' : 'no');
        text('approaching', data.ai_bear_approaching ? 'yes' : 'no');
        text('confidence', data.ai_bear_confidence == null ? '-' : Number(data.ai_bear_confidence).toFixed(2));
        text('area', data.ai_bear_box_area_ratio == null ? '-' : (Number(data.ai_bear_box_area_ratio) * 100).toFixed(1) + '%');
        text('inference', data.inference_time_ms == null ? '-' : Number(data.inference_time_ms).toFixed(1));
      }
      refreshStatus();
      setInterval(refreshStatus, 1000);
    </script>
  </body>
</html>
"""


@dataclass
class SharedCameraAiState:
    latest_jpeg: bytes | None = None
    latest_record: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    def update_frame(self, jpeg: bytes, record: dict[str, Any]) -> None:
        with self.lock:
            self.latest_jpeg = jpeg
            self.latest_record = record
            self.error_message = None

    def update_status(self, record: dict[str, Any], error_message: str | None = None) -> None:
        with self.lock:
            self.latest_record = record
            self.error_message = error_message

    def snapshot(self) -> tuple[bytes | None, dict[str, Any], str | None]:
        with self.lock:
            return self.latest_jpeg, dict(self.latest_record), self.error_message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run camera AI and serve an SSH-forwardable web viewer."
    )
    parser.add_argument("--config", default="raspberry_pi/camera_ai/config.camera_ai.yaml")
    parser.add_argument("--device", default=None)
    parser.add_argument("--camera", type=int, default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--jpeg-quality", type=int, default=75)
    parser.add_argument("--terminal-status", action="store_true")
    return parser


def format_detection_label(detection: dict[str, Any]) -> str:
    class_name = str(detection.get("class_name", "object"))
    confidence = float(detection.get("confidence", 0.0))
    area_percent = float(detection.get("box_area_ratio", 0.0)) * 100.0
    return f"{class_name} {confidence:.2f} area={area_percent:.1f}%"


def draw_detections(cv2, frame, detections: list[dict[str, Any]], record: dict[str, Any]):
    annotated = frame.copy()
    for detection in detections:
        x1, y1, x2, y2 = [int(round(value)) for value in detection.get("bbox_xyxy", [])]
        color = (0, 220, 0) if str(detection.get("class_name", "")).lower() == "bear" else (255, 180, 0)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            annotated,
            format_detection_label(detection),
            (max(0, x1), max(18, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )

    event = str(record.get("event", "-"))
    approaching = "APPROACHING" if record.get("ai_bear_approaching") else "watching"
    cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 34), (0, 0, 0), -1)
    cv2.putText(
        annotated,
        f"{event} | {approaching}",
        (8, 23),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return annotated


def encode_jpeg(cv2, frame, jpeg_quality: int) -> bytes:
    quality = max(20, min(95, int(jpeg_quality)))
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("failed to encode frame as JPEG")
    return buffer.tobytes()


def terminal_status(record: dict[str, Any]) -> str:
    return (
        f"{record.get('timestamp', '-')} "
        f"event={record.get('event', '-')} "
        f"bear={'yes' if record.get('ai_bear_detected') else 'no'} "
        f"approaching={'yes' if record.get('ai_bear_approaching') else 'no'} "
        f"conf={record.get('ai_bear_confidence')} "
        f"infer_ms={record.get('inference_time_ms')}"
    )


def publish_and_update(
    publisher: AiStatePublisher,
    shared_state: SharedCameraAiState,
    state: AiState,
    *,
    terminal_status_enabled: bool,
    error_message: str | None = None,
) -> dict[str, Any]:
    record = publisher.publish(state)
    if terminal_status_enabled:
        print(terminal_status(record), flush=True)
    shared_state.update_status(record, error_message=error_message)
    return record


def camera_ai_worker(args: argparse.Namespace, shared_state: SharedCameraAiState) -> None:
    import cv2

    try:
        config = load_config(config_path(args.config))
        output_config = config.get("output", {})
        publisher = AiStatePublisher(
            jsonl_stdout=False,
            save_csv=bool(output_config.get("save_csv", True)),
            csv_path=repo_path(output_config.get("csv_path", "data/logs/camera_ai_log.csv")),
        )
        camera_config = config.get("camera", {})
        camera_source = resolve_camera_source(
            camera_config,
            camera_override=args.camera,
            device_override=args.device,
        )
        result, _ = open_camera_with_fallbacks(
            cv2,
            camera_source=camera_source,
            backend_name=str(camera_config.get("backend", "v4l2")),
            profiles=fallback_profiles(camera_config),
            read_test=True,
            retries=int(camera_config.get("read_retries", 3)),
            retry_delay_sec=float(camera_config.get("retry_delay_sec", 0.1)),
        )
        camera_device = str(camera_source)
        if result is None:
            publish_and_update(
                publisher,
                shared_state,
                build_fail_safe_state(
                    camera_device=camera_device,
                    ai_camera_ok=False,
                    ai_model_ok=False,
                    event="AI_CAMERA_OPEN_ERROR",
                ),
                terminal_status_enabled=args.terminal_status,
                error_message="camera could not be opened",
            )
            return

        capture = result.capture
        inference_config = config.get("inference", {})
        detector = YoloBearDetector(
            resolve_model_path(inference_config, args.model),
            input_size=int(inference_config.get("input_size", 256)),
            confidence_floor=float(inference_config.get("confidence_floor", 0.05)),
            device=inference_config.get("device", "cpu"),
            class_ids=inference_config.get("class_ids", []),
        )
        approach_logic = ApproachLogic(
            ApproachDetectionConfig.from_mapping(config.get("approach_detection", {}))
        )
        inference_interval_sec = float(inference_config.get("inference_interval_sec", 0.5))

        try:
            while True:
                ok, frame = read_frame_with_retries(capture)
                if not ok or frame is None:
                    publish_and_update(
                        publisher,
                        shared_state,
                        build_fail_safe_state(
                            camera_device=camera_device,
                            ai_camera_ok=False,
                            ai_model_ok=True,
                            event="AI_CAMERA_FRAME_ERROR",
                        ),
                        terminal_status_enabled=args.terminal_status,
                        error_message="camera frame read failed",
                    )
                    time.sleep(1.0)
                    continue

                started_at = time.perf_counter()
                detections = detector.detect(frame)
                inference_time_ms = (time.perf_counter() - started_at) * 1000.0
                decision = approach_logic.update(detections)
                record = publisher.publish(
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
                    )
                )
                if args.terminal_status:
                    print(terminal_status(record), flush=True)
                annotated = draw_detections(cv2, frame, detections, record)
                shared_state.update_frame(
                    encode_jpeg(cv2, annotated, args.jpeg_quality),
                    record,
                )
                time.sleep(inference_interval_sec)
        finally:
            capture.release()
    except Exception as exc:
        shared_state.update_status(
            {
                "event": "AI_WEB_VIEWER_ERROR",
                "ai_camera_ok": False,
                "ai_model_ok": False,
                "ai_bear_detected": False,
                "ai_bear_approaching": False,
                "inference_time_ms": None,
            },
            error_message=str(exc),
        )


def create_app(shared_state: SharedCameraAiState):
    from flask import Flask, Response, jsonify, render_template_string

    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template_string(HTML_TEMPLATE)

    @app.route("/status.json")
    def status_json():
        _, record, error_message = shared_state.snapshot()
        payload = dict(record)
        if error_message:
            payload["error_message"] = error_message
        return jsonify(payload)

    @app.route("/video.mjpg")
    def video_mjpg():
        def generate():
            boundary = b"--frame\r\n"
            while True:
                jpeg, _, _ = shared_state.snapshot()
                if jpeg is not None:
                    yield (
                        boundary
                        + b"Content-Type: image/jpeg\r\n"
                        + f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii")
                        + jpeg
                        + b"\r\n"
                    )
                time.sleep(0.1)

        return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

    return app


def main() -> int:
    args = build_parser().parse_args()
    shared_state = SharedCameraAiState()
    worker = threading.Thread(
        target=camera_ai_worker,
        args=(args, shared_state),
        daemon=True,
    )
    worker.start()
    app = create_app(shared_state)
    app.run(host=args.host, port=args.port, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
