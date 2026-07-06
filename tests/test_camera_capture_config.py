from raspberry_pi.camera_ai import camera_capture
from raspberry_pi.camera_ai.camera_capture import (
    DEFAULT_CAMERA_DEVICE,
    CameraProfile,
    OpenCvCameraDriver,
    camera_driver_from_config,
    device_caps_has_video_capture,
    fallback_profiles,
    resolve_camera_source,
    select_camera_device,
)


class FakeFrame:
    shape = (240, 320, 3)

    def __init__(self, brightness: float) -> None:
        self.brightness = brightness

    def mean(self) -> float:
        return self.brightness

    def copy(self):
        return FakeFrame(self.brightness)


class FakeCapture:
    def __init__(self, frames, *, opened: bool = True) -> None:
        self.frames = list(frames)
        self.opened = opened
        self.released = False
        self.set_calls = []

    def isOpened(self) -> bool:
        return self.opened and not self.released

    def set(self, prop_id, value) -> None:
        self.set_calls.append((prop_id, value))

    def get(self, prop_id):
        values = {
            FakeCv2.CAP_PROP_FRAME_WIDTH: 320,
            FakeCv2.CAP_PROP_FRAME_HEIGHT: 240,
            FakeCv2.CAP_PROP_FPS: 5,
            FakeCv2.CAP_PROP_FOURCC: 1196444237,
        }
        return values.get(prop_id, 0)

    def read(self):
        if not self.frames:
            return False, None
        frame = self.frames.pop(0)
        if frame is None:
            return False, None
        return True, frame

    def release(self) -> None:
        self.released = True


class FakeCv2:
    CAP_ANY = 0
    CAP_V4L2 = 200
    CAP_PROP_FOURCC = 6
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4
    CAP_PROP_FPS = 5
    CAP_PROP_BUFFERSIZE = 38
    COLOR_BGR2GRAY = 10

    def __init__(self, captures) -> None:
        self.captures = list(captures)
        self.created_captures = []

    def VideoCapture(self, camera_source, backend_id):
        capture = self.captures.pop(0)
        capture.camera_source = camera_source
        capture.backend_id = backend_id
        self.created_captures.append(capture)
        return capture

    def VideoWriter_fourcc(self, *characters) -> int:
        return 1196444237

    def cvtColor(self, frame, _color_code):
        return frame


def test_default_camera_source_is_video0_path():
    assert resolve_camera_source({}) == DEFAULT_CAMERA_DEVICE
    assert resolve_camera_source({}) != "/dev/video1"


def test_camera_device_config_uses_video0_path():
    assert resolve_camera_source({"device": "/dev/video0"}) == "/dev/video0"


def test_auto_camera_device_selects_buffalo_video_capture_node():
    selected_device = select_camera_device(
        ["/dev/video1", "/dev/video0"],
        capture_checker=lambda device: device == "/dev/video0",
        usb_id_lookup=lambda _device: ("0411", "02da"),
    )

    assert selected_device == "/dev/video0"


def test_device_caps_parser_rejects_metadata_only_node():
    metadata_info = """
Driver Info:
\tDriver name      : uvcvideo
\tDevice Caps      : 0x04a00000
\t\tMetadata Capture
\t\tStreaming
Media Driver Info:
"""
    capture_info = """
Driver Info:
\tDriver name      : uvcvideo
\tDevice Caps      : 0x04200001
\t\tVideo Capture
\t\tStreaming
Media Driver Info:
"""

    assert device_caps_has_video_capture(metadata_info) is False
    assert device_caps_has_video_capture(capture_info) is True


def test_auto_device_config_resolves_with_discovery(monkeypatch):
    monkeypatch.setattr(
        camera_capture,
        "available_video_devices",
        lambda: ["/dev/video0", "/dev/video1"],
    )
    monkeypatch.setattr(
        camera_capture,
        "video_device_has_video_capture",
        lambda device: device == "/dev/video0",
    )
    monkeypatch.setattr(
        camera_capture,
        "video_device_usb_ids",
        lambda _device: ("0411", "02da"),
    )

    assert resolve_camera_source({"device": "auto"}) == "/dev/video0"


def test_explicit_device_override_is_respected():
    assert (
        resolve_camera_source(
            {"device": "/dev/video0"},
            device_override="/dev/video2",
        )
        == "/dev/video2"
    )


def test_fallback_profiles_try_mjpg_before_yuyv():
    profiles = fallback_profiles(
        {
            "width": 640,
            "height": 480,
            "fps": 15,
            "fourcc": "MJPG",
        }
    )

    assert profiles[:3] == [
        CameraProfile(640, 480, 15, "MJPG"),
        CameraProfile(320, 240, 15, "MJPG"),
        CameraProfile(640, 480, 15, "YUYV"),
    ]


def test_opencv_camera_driver_reads_stable_frame():
    capture = FakeCapture([FakeFrame(90), FakeFrame(95)])
    driver = OpenCvCameraDriver(
        FakeCv2([capture]),
        camera_source="/dev/video0",
        backend_name="v4l2",
        profiles=[CameraProfile(320, 240, 5, "MJPG")],
        read_retries=1,
        retry_delay_sec=0,
        dark_frame_mean_threshold=30,
        reopen_delay_sec=0,
    )

    result = driver.read_frame()

    assert result.ok is True
    assert result.event == "AI_CAMERA_FRAME_OK"
    assert result.brightness_mean == 95
    assert result.camera_device == "/dev/video0"
    assert result.selected_profile == CameraProfile(320, 240, 5, "MJPG")
    assert capture.released is False


def test_opencv_camera_driver_reopens_after_dark_frame():
    first_capture = FakeCapture([FakeFrame(90), FakeFrame(0)])
    reopened_capture = FakeCapture([FakeFrame(90), FakeFrame(95)])
    driver = OpenCvCameraDriver(
        FakeCv2([first_capture, reopened_capture]),
        camera_source="/dev/video0",
        backend_name="v4l2",
        profiles=[CameraProfile(320, 240, 5, "MJPG")],
        read_retries=1,
        retry_delay_sec=0,
        dark_frame_mean_threshold=30,
        dark_frame_recovery_sec=0,
        reopen_delay_sec=0,
    )

    result = driver.read_frame()

    assert result.ok is False
    assert result.event == "AI_CAMERA_DARK_FRAME"
    assert result.brightness_mean == 0
    assert result.reopen_attempted is True
    assert result.reopen_ok is True
    assert first_capture.released is True
    assert driver.capture is reopened_capture
    assert driver.reopen_count == 1


def test_opencv_camera_driver_reopens_after_read_failures():
    first_capture = FakeCapture([FakeFrame(90), None])
    reopened_capture = FakeCapture([FakeFrame(90), FakeFrame(95)])
    driver = OpenCvCameraDriver(
        FakeCv2([first_capture, reopened_capture]),
        camera_source="/dev/video0",
        backend_name="v4l2",
        profiles=[CameraProfile(320, 240, 5, "MJPG")],
        read_retries=1,
        retry_delay_sec=0,
        dark_frame_mean_threshold=30,
        reopen_delay_sec=0,
        max_consecutive_read_failures=1,
    )

    result = driver.read_frame()

    assert result.ok is False
    assert result.event == "AI_CAMERA_FRAME_ERROR"
    assert result.reopen_attempted is True
    assert result.reopen_ok is True
    assert first_capture.released is True
    assert driver.capture is reopened_capture


def test_camera_driver_config_maps_fail_safe_recovery_options():
    fake_cv2 = FakeCv2([FakeCapture([FakeFrame(90), FakeFrame(95)])])
    driver = camera_driver_from_config(
        fake_cv2,
        {
            "device": "/dev/video2",
            "backend": "v4l2",
            "width": 320,
            "height": 240,
            "fps": 5,
            "fourcc": "MJPG",
            "read_retries": 1,
            "retry_delay_sec": 0,
        },
        fail_safe_config={
            "dark_frame_mean_threshold": 22,
            "dark_frame_recovery_sec": 1.5,
            "camera_reopen_delay_sec": 0,
            "max_consecutive_read_failures": 2,
        },
    )

    assert driver.camera_device == "/dev/video2"
    assert driver.dark_frame_mean_threshold == 22
    assert driver.dark_frame_recovery_sec == 1.5
    assert driver.reopen_delay_sec == 0
    assert driver.max_consecutive_read_failures == 2
