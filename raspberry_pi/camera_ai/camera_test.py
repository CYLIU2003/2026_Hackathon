from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .camera_capture import (
        DEFAULT_CAMERA_DEVICE,
        CameraProfile,
        actual_fourcc,
        fallback_profiles,
        open_camera_with_fallbacks,
        resolve_camera_source,
    )
except ImportError:
    from camera_capture import (
        DEFAULT_CAMERA_DEVICE,
        CameraProfile,
        actual_fourcc,
        fallback_profiles,
        open_camera_with_fallbacks,
        resolve_camera_source,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture one test frame from /dev/video0 without starting YOLO."
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=None,
        help="Explicit OpenCV camera index override. Default uses /dev/video0.",
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_CAMERA_DEVICE,
        help="Linux video device path. Target hardware default is /dev/video0.",
    )
    parser.add_argument("--backend", choices=["v4l2", "any"], default="v4l2")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--fourcc", default="MJPG", help="Camera pixel format, for example MJPG or YUYV.")
    parser.add_argument(
        "--single-profile",
        action="store_true",
        help="Only try the requested width/height/fps/fourcc instead of safe fallbacks.",
    )
    parser.add_argument("--retries", type=int, default=3, help="Frame read retry count.")
    parser.add_argument("--retry-delay-sec", type=float, default=0.1)
    parser.add_argument("--output", default="outputs/camera_test.jpg")
    parser.add_argument("--no-save", action="store_true")
    return parser


def available_video_devices() -> list[str]:
    return [str(path) for path in sorted(Path("/dev").glob("video*"))]


def requested_profile(args) -> CameraProfile:
    return CameraProfile(
        width=args.width,
        height=args.height,
        fps=args.fps,
        fourcc=args.fourcc,
    )


def main() -> int:
    args = build_parser().parse_args()

    try:
        import cv2
    except ImportError:
        print("ERROR: opencv-python is not installed.")
        return 1

    camera_config = {
        "device": args.device,
        "width": args.width,
        "height": args.height,
        "fps": args.fps,
        "fourcc": args.fourcc,
    }
    camera_source = resolve_camera_source(
        camera_config,
        camera_override=args.camera,
        device_override=args.device if args.camera is None else None,
    )
    profiles = (
        [requested_profile(args)]
        if args.single_profile
        else fallback_profiles(camera_config)
    )

    print(f"available_video_devices={available_video_devices()}")
    print(f"camera_source={camera_source}")
    print(f"backend={args.backend}")
    print("candidate_profiles=" + ", ".join(profile.label() for profile in profiles))

    result, frame = open_camera_with_fallbacks(
        cv2,
        camera_source=camera_source,
        backend_name=args.backend,
        profiles=profiles,
        read_test=True,
        retries=args.retries,
        retry_delay_sec=args.retry_delay_sec,
    )
    if result is None:
        print(f"ERROR: camera could not be opened: {camera_source}")
        print("Try: v4l2-ctl --list-devices")
        print(f"Try: v4l2-ctl --device={camera_source} --list-formats-ext")
        print(f"Try: v4l2-ctl --device={camera_source} --set-fmt-video=width=640,height=480,pixelformat=MJPG --stream-mmap --stream-count=30")
        print(f"Try: v4l2-ctl --device={camera_source} --set-fmt-video=width=320,height=240,pixelformat=MJPG --stream-mmap --stream-count=30")
        return 1

    output_path = Path(args.output)
    if not args.no_save:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), frame)

    print("Camera OK")
    print(f"selected_profile={result.selected_profile.label()}")
    print(f"frame shape: {frame.shape}")
    print(f"frame_width={result.actual_width}")
    print(f"frame_height={result.actual_height}")
    print(f"fps_setting={result.actual_fps:.2f}")
    print(f"fourcc={result.actual_fourcc or actual_fourcc(cv2, result.capture)}")
    if not args.no_save:
        print(f"saved_frame={output_path}")
    result.capture.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
