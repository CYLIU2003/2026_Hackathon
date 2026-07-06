from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

AUTO_CAMERA_DEVICE = "auto"
DEFAULT_CAMERA_DEVICE = "/dev/video0"
BUFFALO_BSW500M_VENDOR_ID = "0411"
BUFFALO_BSW500M_PRODUCT_ID = "02da"


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


@dataclass(frozen=True)
class CameraFrameResult:
    ok: bool
    frame: Any | None
    camera_source: str | int
    camera_device: str
    event: str
    brightness_mean: float | None = None
    selected_profile: CameraProfile | None = None
    reopen_attempted: bool = False
    reopen_ok: bool | None = None
    consecutive_read_failures: int = 0


def resolve_camera_source(
    camera_config: dict,
    *,
    camera_override: int | None = None,
    device_override: str | None = None,
) -> str | int:
    if device_override:
        if is_auto_camera_device(device_override):
            return resolve_auto_camera_device(camera_config)
        return device_override
    if camera_override is not None:
        return camera_override
    configured_device = str(camera_config.get("device") or DEFAULT_CAMERA_DEVICE)
    if is_auto_camera_device(configured_device):
        return resolve_auto_camera_device(camera_config)
    return configured_device


def is_auto_camera_device(device: str) -> bool:
    return device.lower() in {AUTO_CAMERA_DEVICE, "bsw500m", "buffalo_bsw500m"}


def available_video_devices(dev_dir: str | Path = "/dev") -> list[str]:
    return [
        str(path)
        for path in sorted(Path(dev_dir).glob("video*"), key=video_device_sort_key)
    ]


def video_device_sort_key(path: str | Path) -> tuple[int, str]:
    name = Path(path).name
    if name.startswith("video") and name[5:].isdigit():
        return (int(name[5:]), name)
    return (9999, name)


def resolve_auto_camera_device(camera_config: dict) -> str:
    vendor_id = str(
        camera_config.get("preferred_usb_vendor_id", BUFFALO_BSW500M_VENDOR_ID)
    ).lower()
    product_id = str(
        camera_config.get("preferred_usb_product_id", BUFFALO_BSW500M_PRODUCT_ID)
    ).lower()
    return select_camera_device(
        available_video_devices(),
        preferred_usb_vendor_id=vendor_id,
        preferred_usb_product_id=product_id,
    )


def select_camera_device(
    devices: Iterable[str],
    *,
    capture_checker=None,
    usb_id_lookup=None,
    preferred_usb_vendor_id: str = BUFFALO_BSW500M_VENDOR_ID,
    preferred_usb_product_id: str = BUFFALO_BSW500M_PRODUCT_ID,
) -> str:
    capture_checker = capture_checker or video_device_has_video_capture
    usb_id_lookup = usb_id_lookup or video_device_usb_ids
    sorted_devices = sorted(devices, key=video_device_sort_key)
    capture_devices: list[str] = []
    unknown_devices: list[str] = []
    for device in sorted_devices:
        capture_status = capture_checker(device)
        if capture_status is False:
            continue
        if capture_status is True:
            capture_devices.append(device)
        else:
            unknown_devices.append(device)

    candidates = capture_devices or unknown_devices or sorted_devices
    preferred_vendor = preferred_usb_vendor_id.lower()
    preferred_product = preferred_usb_product_id.lower()
    for device in candidates:
        vendor_id, product_id = usb_id_lookup(device)
        if vendor_id == preferred_vendor and product_id == preferred_product:
            return device

    if DEFAULT_CAMERA_DEVICE in candidates:
        return DEFAULT_CAMERA_DEVICE
    return candidates[0] if candidates else DEFAULT_CAMERA_DEVICE


def video_device_has_video_capture(device: str) -> bool | None:
    info_text = v4l2_device_info(device)
    if not info_text:
        return None
    return device_caps_has_video_capture(info_text)


def v4l2_device_info(device: str) -> str:
    if shutil.which("v4l2-ctl") is None:
        return ""
    try:
        completed = subprocess.run(
            ["v4l2-ctl", f"--device={device}", "--info"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout


def device_caps_has_video_capture(info_text: str) -> bool | None:
    in_device_caps = False
    for line in info_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Device Caps"):
            in_device_caps = True
            continue
        if not in_device_caps:
            continue
        if stripped and not line.startswith("\t"):
            break
        if stripped == "Video Capture":
            return True
        if stripped == "Metadata Capture":
            continue
    return False if in_device_caps else None


def video_device_usb_ids(device: str) -> tuple[str | None, str | None]:
    video_name = Path(device).name
    sysfs_path = Path("/sys/class/video4linux") / video_name / "device"
    if not sysfs_path.exists():
        return None, None
    resolved_path = sysfs_path.resolve()
    for path in [resolved_path, *resolved_path.parents]:
        vendor_path = path / "idVendor"
        product_path = path / "idProduct"
        if vendor_path.exists() or product_path.exists():
            return read_sysfs_text(vendor_path), read_sysfs_text(product_path)
    return None, None


def read_sysfs_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip().lower()
    except OSError:
        return None


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
        CameraProfile(320, 240, 5, "MJPG"),
        CameraProfile(320, 240, 5, "YUYV"),
        CameraProfile(640, 480, 5, "MJPG"),
        CameraProfile(640, 480, 5, "YUYV"),
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


def frame_brightness_mean(cv2, frame) -> float:
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(gray_frame.mean())


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


class OpenCvCameraDriver:
    """Owns OpenCV capture lifecycle and keeps recovery logic out of app loops."""

    def __init__(
        self,
        cv2,
        *,
        camera_source: str | int,
        backend_name: str,
        profiles: Iterable[CameraProfile],
        read_retries: int = 3,
        retry_delay_sec: float = 0.1,
        dark_frame_mean_threshold: float | None = 8.0,
        dark_frame_recovery_sec: float = 4.0,
        reopen_delay_sec: float = 1.0,
        max_consecutive_read_failures: int = 3,
    ) -> None:
        self.cv2 = cv2
        self.camera_source = camera_source
        self.backend_name = backend_name
        self.profiles = list(profiles)
        self.read_retries = max(1, int(read_retries))
        self.retry_delay_sec = max(0.0, float(retry_delay_sec))
        self.dark_frame_mean_threshold = dark_frame_mean_threshold
        self.dark_frame_recovery_sec = max(0.0, float(dark_frame_recovery_sec))
        self.reopen_delay_sec = max(0.0, float(reopen_delay_sec))
        self.max_consecutive_read_failures = max(1, int(max_consecutive_read_failures))
        self.capture = None
        self.open_result: CameraOpenResult | None = None
        self.consecutive_read_failures = 0
        self.dark_frame_started_at: float | None = None
        self.reopen_count = 0

    @property
    def camera_device(self) -> str:
        return str(self.camera_source)

    @property
    def selected_profile(self) -> CameraProfile | None:
        if self.open_result is None:
            return None
        return self.open_result.selected_profile

    def open(self) -> bool:
        self.close()
        result, _ = open_camera_with_fallbacks(
            self.cv2,
            camera_source=self.camera_source,
            backend_name=self.backend_name,
            profiles=self.profiles,
            read_test=True,
            retries=self.read_retries,
            retry_delay_sec=self.retry_delay_sec,
        )
        if result is None:
            self.capture = None
            self.open_result = None
            return False

        self.capture = result.capture
        self.open_result = result
        self.consecutive_read_failures = 0
        self.dark_frame_started_at = None
        return True

    def close(self) -> None:
        if self.capture is None:
            return
        try:
            self.capture.release()
        finally:
            self.capture = None
            self.open_result = None

    def read_frame(self) -> CameraFrameResult:
        if self.capture is None or not self.capture.isOpened():
            if not self.open():
                return self._result(False, None, "AI_CAMERA_OPEN_ERROR")

        ok, frame = read_frame_with_retries(
            self.capture,
            retries=self.read_retries,
            retry_delay_sec=self.retry_delay_sec,
        )
        if not ok or frame is None:
            self.consecutive_read_failures += 1
            if self.consecutive_read_failures >= self.max_consecutive_read_failures:
                return self._reopen_result("AI_CAMERA_FRAME_ERROR", None, None)
            return self._result(False, None, "AI_CAMERA_FRAME_ERROR")

        self.consecutive_read_failures = 0
        brightness_mean = self._brightness_mean(frame)
        dark_frame = (
            brightness_mean is not None
            and self.dark_frame_mean_threshold is not None
            and brightness_mean < self.dark_frame_mean_threshold
        )
        if dark_frame:
            now_monotonic = time.monotonic()
            if self.dark_frame_started_at is None:
                self.dark_frame_started_at = now_monotonic
            if now_monotonic - self.dark_frame_started_at >= self.dark_frame_recovery_sec:
                return self._reopen_result(
                    "AI_CAMERA_DARK_FRAME",
                    frame,
                    brightness_mean,
                )
        else:
            self.dark_frame_started_at = None

        return self._result(
            True,
            frame,
            "AI_CAMERA_FRAME_OK",
            brightness_mean=brightness_mean,
        )

    def _brightness_mean(self, frame) -> float | None:
        if self.dark_frame_mean_threshold is None:
            return None
        try:
            return frame_brightness_mean(self.cv2, frame)
        except Exception:
            return None

    def _reopen_result(
        self,
        event: str,
        frame,
        brightness_mean: float | None,
    ) -> CameraFrameResult:
        self.close()
        if self.reopen_delay_sec > 0:
            time.sleep(self.reopen_delay_sec)
        self.reopen_count += 1
        reopen_ok = self.open()
        if reopen_ok:
            self.dark_frame_started_at = None
            self.consecutive_read_failures = 0
        return self._result(
            False,
            frame,
            event,
            brightness_mean=brightness_mean,
            reopen_attempted=True,
            reopen_ok=reopen_ok,
        )

    def _result(
        self,
        ok: bool,
        frame,
        event: str,
        *,
        brightness_mean: float | None = None,
        reopen_attempted: bool = False,
        reopen_ok: bool | None = None,
    ) -> CameraFrameResult:
        return CameraFrameResult(
            ok=ok,
            frame=frame,
            camera_source=self.camera_source,
            camera_device=self.camera_device,
            event=event,
            brightness_mean=brightness_mean,
            selected_profile=self.selected_profile,
            reopen_attempted=reopen_attempted,
            reopen_ok=reopen_ok,
            consecutive_read_failures=self.consecutive_read_failures,
        )


def camera_driver_from_config(
    cv2,
    camera_config: dict,
    *,
    fail_safe_config: dict | None = None,
    camera_override: int | None = None,
    device_override: str | None = None,
) -> OpenCvCameraDriver:
    fail_safe_config = fail_safe_config or {}
    camera_source = resolve_camera_source(
        camera_config,
        camera_override=camera_override,
        device_override=device_override,
    )
    dark_frame_mean_threshold = fail_safe_config.get("dark_frame_mean_threshold", 8.0)
    if dark_frame_mean_threshold is not None:
        dark_frame_mean_threshold = float(dark_frame_mean_threshold)
    return OpenCvCameraDriver(
        cv2,
        camera_source=camera_source,
        backend_name=str(camera_config.get("backend", "v4l2")),
        profiles=fallback_profiles(camera_config),
        read_retries=int(camera_config.get("read_retries", 3)),
        retry_delay_sec=float(camera_config.get("retry_delay_sec", 0.1)),
        dark_frame_mean_threshold=dark_frame_mean_threshold,
        dark_frame_recovery_sec=float(
            fail_safe_config.get("dark_frame_recovery_sec", 4.0)
        ),
        reopen_delay_sec=float(fail_safe_config.get("camera_reopen_delay_sec", 1.0)),
        max_consecutive_read_failures=int(
            fail_safe_config.get(
                "max_consecutive_read_failures",
                camera_config.get("max_consecutive_read_failures", 3),
            )
        ),
    )
