from raspberry_pi.camera_ai.camera_capture import (
    DEFAULT_CAMERA_DEVICE,
    CameraProfile,
    fallback_profiles,
    resolve_camera_source,
)


def test_default_camera_source_is_video0_path():
    assert resolve_camera_source({}) == DEFAULT_CAMERA_DEVICE
    assert resolve_camera_source({}) != "/dev/video1"


def test_camera_device_config_uses_video0_path():
    assert resolve_camera_source({"device": "/dev/video0"}) == "/dev/video0"


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
