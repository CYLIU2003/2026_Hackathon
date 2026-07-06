import sys
from pathlib import Path

import cv2
import numpy as np

CAMERA_AI_DIR = Path(__file__).resolve().parents[1] / "raspberry_pi" / "camera_ai"
sys.path.insert(0, str(CAMERA_AI_DIR))

from run_camera_ai import prepare_display_frame


def test_prepare_display_frame_preserves_color_channels():
    frame = np.zeros((24, 32, 3), dtype=np.uint8)
    frame[:, :16] = (20, 80, 180)
    frame[:, 16:] = (180, 60, 20)

    display_frame = prepare_display_frame(cv2, frame)
    blue, green, red = cv2.split(display_frame)

    assert display_frame.shape == frame.shape
    assert float(cv2.absdiff(blue, green).mean()) > 1.0
    assert float(cv2.absdiff(green, red).mean()) > 1.0
