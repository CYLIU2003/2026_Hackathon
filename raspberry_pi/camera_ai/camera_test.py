from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture one test frame from a USB camera.")
    parser.add_argument("--camera", type=int, default=None, help="OpenCV camera index.")
    parser.add_argument("--device", default=None, help="Linux video device path, for example /dev/video0.")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--debug-dir", default="data/debug_frames")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        import cv2
    except ImportError:
        print("ERROR: opencv-python is not installed.")
        return 1

    camera_source = args.device if args.device else args.camera
    if camera_source is None:
        camera_source = 0

    backend = cv2.CAP_V4L2 if os.name == "posix" else cv2.CAP_ANY
    capture = cv2.VideoCapture(camera_source, backend)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    capture.set(cv2.CAP_PROP_FPS, args.fps)

    if not capture.isOpened():
        print(f"ERROR: camera could not be opened: {camera_source}")
        return 1

    ok, frame = capture.read()
    if not ok or frame is None:
        capture.release()
        print(f"ERROR: camera opened but no frame was captured: {camera_source}")
        return 1

    actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = capture.get(cv2.CAP_PROP_FPS)

    debug_dir = Path(args.debug_dir)
    debug_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = debug_dir / f"camera_test_{timestamp}.jpg"
    cv2.imwrite(str(output_path), frame)
    capture.release()

    print(f"camera_source={camera_source}")
    print(f"frame_width={actual_width}")
    print(f"frame_height={actual_height}")
    print(f"fps_setting={actual_fps:.2f}")
    print(f"saved_frame={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

