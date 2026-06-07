from __future__ import annotations

import argparse
import os
import time
from datetime import datetime
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture one test frame from a USB camera.")
    parser.add_argument("--camera", type=int, default=None, help="OpenCV camera index.")
    parser.add_argument("--device", default=None, help="Linux video device path, for example /dev/video0.")
    parser.add_argument("--backend", choices=["v4l2", "any"], default="v4l2")
    parser.add_argument("--width", type=int, default=320)
    parser.add_argument("--height", type=int, default=240)
    parser.add_argument("--fps", type=int, default=5)
    parser.add_argument("--fourcc", default="YUYV", help="Camera pixel format, for example MJPG or YUYV.")
    parser.add_argument("--auto-profiles", action="store_true", help="Try common USB camera profiles.")
    parser.add_argument("--retries", type=int, default=1, help="Frame read retry count.")
    parser.add_argument("--retry-delay-sec", type=float, default=0.1)
    parser.add_argument("--debug-dir", default="data/debug_frames")
    return parser


def read_frame_with_retries(capture, *, retries: int, retry_delay_sec: float):
    for _ in range(max(1, retries)):
        ok, frame = capture.read()
        if ok and frame is not None:
            return ok, frame
        time.sleep(max(0.0, retry_delay_sec))
    return False, None


def backend_id(cv2, backend_name: str) -> int:
    if backend_name == "any":
        return cv2.CAP_ANY
    return cv2.CAP_V4L2 if os.name == "posix" else cv2.CAP_ANY


def open_capture(cv2, camera_source, args, *, width: int, height: int, fps: int, fourcc: str):
    capture = cv2.VideoCapture(camera_source, backend_id(cv2, args.backend))
    if fourcc:
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc[:4]))
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    capture.set(cv2.CAP_PROP_FPS, fps)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return capture


def candidate_profiles(args) -> list[tuple[int, int, int, str]]:
    requested = (args.width, args.height, args.fps, args.fourcc)
    if not args.auto_profiles:
        return [requested]

    common_profiles = [
        requested,
        (320, 240, 5, "YUYV"),
        (320, 240, 5, "MJPG"),
        (640, 480, 30, "MJPG"),
        (640, 480, 15, "MJPG"),
        (320, 240, 30, "MJPG"),
        (320, 240, 15, "MJPG"),
        (640, 480, 30, "YUYV"),
        (640, 480, 15, "YUYV"),
        (320, 240, 30, "YUYV"),
        (320, 240, 15, "YUYV"),
    ]
    return list(dict.fromkeys(common_profiles))


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

    capture = None
    selected_profile = None
    ok = False
    frame = None
    for width, height, fps, fourcc in candidate_profiles(args):
        if capture is not None:
            capture.release()
        capture = open_capture(
            cv2,
            camera_source,
            args,
            width=width,
            height=height,
            fps=fps,
            fourcc=fourcc,
        )

        if not capture.isOpened():
            continue

        ok, frame = read_frame_with_retries(
            capture,
            retries=args.retries,
            retry_delay_sec=args.retry_delay_sec,
        )
        if ok and frame is not None:
            selected_profile = (width, height, fps, fourcc)
            break

    if capture is None or not capture.isOpened():
        print(f"ERROR: camera could not be opened: {camera_source}")
        print("Try: --backend any")
        return 1

    if not ok or frame is None or selected_profile is None:
        capture.release()
        print(f"ERROR: camera opened but no frame was captured: {camera_source}")
        print("Try: v4l2-ctl --list-devices")
        print(f"Try: v4l2-ctl --device={camera_source} --list-formats-ext")
        print(f"Try: v4l2-ctl --device={camera_source} --stream-mmap --stream-count=10 --stream-to=/tmp/camera-test.raw")
        print("Try another device, for example: --device /dev/video1")
        print("Try OpenCV default backend: --backend any")
        print("Try automatic profiles: --auto-profiles")
        print("Try another format, for example: --fourcc YUYV --width 640 --height 480")
        return 1

    actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = capture.get(cv2.CAP_PROP_FPS)
    actual_fourcc_value = int(capture.get(cv2.CAP_PROP_FOURCC))
    actual_fourcc = "".join(
        chr((actual_fourcc_value >> 8 * index) & 0xFF) for index in range(4)
    )

    debug_dir = Path(args.debug_dir)
    debug_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = debug_dir / f"camera_test_{timestamp}.jpg"
    cv2.imwrite(str(output_path), frame)
    capture.release()

    print(f"camera_source={camera_source}")
    print(f"backend={args.backend}")
    print(f"selected_profile={selected_profile[0]}x{selected_profile[1]} {selected_profile[2]}fps {selected_profile[3]}")
    print(f"frame_width={actual_width}")
    print(f"frame_height={actual_height}")
    print(f"fps_setting={actual_fps:.2f}")
    print(f"fourcc={actual_fourcc}")
    print(f"saved_frame={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
