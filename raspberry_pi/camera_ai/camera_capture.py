from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Iterable

DEFAULT_CAMERA_DEVICE = "/dev/video0"


@dataclass(frozen=True)
class CameraProfile:
    width: int
    height: int
    fps: int
    fourcc: str

    def label(self) -> str:
        return f"{self.width}x{self.height} {self.fps}fps {self.fourcc}"


@dataclass(frozen=True)
class CameraOpenResult:
    capture: Any
    camera_source: str | int
    selected_profile: CameraProfile
    actual_width: int
    actual_height: int
    actual_fps: float
    actual_fourcc: str


def resolve_camera_source(
    camera_config: dict,
    *,
    camera_override: int | None = None,
    device_override: str | None = None,
) -> str | int:
    if device_override:
        return device_override
    if camera_override is not None:
        return camera_override
    return str(camera_config.get("device") or DEFAULT_CAMERA_DEVICE)


def backend_id(cv2, backend_name: str = "v4l2") -> int:
    if backend_name == "any":
        return cv2.CAP_ANY
    return cv2.CAP_V4L2 if os.name == "posix" else cv2.CAP_ANY


def configured_profile(camera_config: dict) -> CameraProfile:
    return CameraProfile(
        width=int(camera_config.get("width", 640)),
        height=int(camera_config.get("height", 480)),
        fps=int(camera_config.get("fps", 15)),
        fourcc=str(camera_config.get("fourcc", "MJPG")),
    )


def fallback_profiles(camera_config: dict | None = None) -> list[CameraProfile]:
    requested = configured_profile(camera_config or {})
    candidates = [
        requested,
        CameraProfile(640, 480, 15, "MJPG"),
        CameraProfile(320, 240, 15, "MJPG"),
        CameraProfile(640, 480, 15, "YUYV"),
        CameraProfile(320, 240, 15, "YUYV"),
    ]
    unique_profiles: list[CameraProfile] = []
    seen: set[tuple[int, int, int, str]] = set()
    for profile in candidates:
        key = (profile.width, profile.height, profile.fps, profile.fourcc)
        if key not in seen:
            seen.add(key)
            unique_profiles.append(profile)
    return unique_profiles


def open_raw_capture(cv2, camera_source: str | int, backend_name: str, profile: CameraProfile):
    capture = cv2.VideoCapture(camera_source, backend_id(cv2, backend_name))
    if profile.fourcc:
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*profile.fourcc[:4]))
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, profile.width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, profile.height)
    capture.set(cv2.CAP_PROP_FPS, profile.fps)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return capture


def read_frame_with_retries(capture, *, retries: int = 3, retry_delay_sec: float = 0.1):
    for _ in range(max(1, retries)):
        ok, frame = capture.read()
        if ok and frame is not None:
            return ok, frame
        time.sleep(max(0.0, retry_delay_sec))
    return False, None


def actual_fourcc(cv2, capture) -> str:
    fourcc_value = int(capture.get(cv2.CAP_PROP_FOURCC))
    return "".join(chr((fourcc_value >> 8 * index) & 0xFF) for index in range(4))


def open_camera_with_fallbacks(
    cv2,
    *,
    camera_source: str | int,
    backend_name: str = "v4l2",
    profiles: Iterable[CameraProfile],
    read_test: bool = True,
    retries: int = 3,
    retry_delay_sec: float = 0.1,
) -> tuple[CameraOpenResult | None, Any | None]:
    for profile in profiles:
        capture = open_raw_capture(cv2, camera_source, backend_name, profile)
        if not capture.isOpened():
            capture.release()
            continue

        frame = None
        if read_test:
            ok, frame = read_frame_with_retries(
                capture,
                retries=retries,
                retry_delay_sec=retry_delay_sec,
            )
            if not ok or frame is None:
                capture.release()
                continue

        result = CameraOpenResult(
            capture=capture,
            camera_source=camera_source,
            selected_profile=profile,
            actual_width=int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            actual_height=int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            actual_fps=float(capture.get(cv2.CAP_PROP_FPS)),
            actual_fourcc=actual_fourcc(cv2, capture),
        )
        return result, frame

    return None, None
