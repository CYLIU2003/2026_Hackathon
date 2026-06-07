# Camera AI Bear Approach Detection

This prototype adds a Raspberry Pi camera AI module for bear approach detection.
It uses a USB camera and a lightweight YOLO model to publish camera-derived state as JSON Lines.

This module is only an additional perception layer. It does not replace the Arduino Uno Q contact-pad logic, `paw_contact`, `raw_contact_value`, resistance/contact thresholds, or the fail-safe `release_state` decision.

## Hardware

- Raspberry Pi 4B 4GB
- BUFFALO BSW500M USB web camera
- No real sensors are required for this camera AI module
- No real animal testing is part of this prototype

## Setup

Run commands from the repository root:

```bash
cd ~/Desktop/2026_Hackathon
```

## Assisted Raspberry Pi Bring-up

Use this order when setting up the module on the Raspberry Pi:

1. Confirm the USB camera is visible to Linux.
2. Create and activate the project virtual environment.
3. Run `camera_test.py` and confirm it saves a debug frame.
4. Place the YOLO model file under `models/`.
5. Run `run_camera_ai.py --once --terminal-status`.
6. Run `run_camera_ai.py --max-iterations 5 --terminal-status` and check JSON Lines plus CSV output.

If any step fails, stop there and capture the command plus output before moving
to the next step. The most useful first outputs to share are:

```bash
uname -a
python3 --version
lsusb
ls /dev/video*
v4l2-ctl --list-devices
groups
```

Do not use `sudo pip`. Keep Python packages inside `.venv`.

## Headless / CUI Operation

The default configuration is safe for Raspberry Pi operation without a monitor:
`use_display` is `false`, so OpenCV does not open a GUI window.

For SSH or Tailscale sessions, use compact terminal status output:

```bash
source .venv/bin/activate
python raspberry_pi/camera_ai/run_camera_ai.py \
  --device /dev/video0 \
  --terminal-status \
  --no-jsonl \
  --max-iterations 5
```

Example CUI status line:

```text
2026-06-07T17:50:00+09:00 event=AI_BEAR_DETECTED camera=ok model=ok bear=yes approaching=no conf=0.82 area=18.0% infer_ms=120.5 device=/dev/video0
```

Use `--terminal-status` without `--no-jsonl` when another process needs JSON
Lines from stdout. The human-readable CUI status is written to stderr, so stdout
remains machine-readable:

```bash
python raspberry_pi/camera_ai/run_camera_ai.py \
  --device /dev/video0 \
  --terminal-status \
  > data/logs/camera_ai.jsonl \
  2> data/logs/camera_ai.status.log
```

To watch the CSV log from a terminal:

```bash
tail -f data/logs/camera_ai_log.csv
```

Install camera tools on Raspberry Pi:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip v4l-utils libgl1 libglib2.0-0
```

Check the camera:

```bash
lsusb
ls /dev/video*
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --all
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

Create a Python virtual environment and install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/camera_ai/requirements.txt
```

Place a small YOLO model at the path configured in `config.camera_ai.yaml`, for example:

```text
models/yolo_bear.pt
```

Model weights are intentionally ignored by Git.

If you only want to confirm the camera first, the YOLO model is not required for
`camera_test.py`. The model is required for `run_camera_ai.py`.

After installing dependencies, verify that Python can import the required
packages:

```bash
source .venv/bin/activate
python - <<'PY'
import cv2
import yaml
import ultralytics
print("cv2", cv2.__version__)
print("yaml", yaml.__version__)
print("ultralytics", ultralytics.__version__)
PY
```

If the camera does not open, make sure the user can access video devices:

```bash
groups
sudo usermod -aG video $USER
```

Log out and log in again after adding the user to the `video` group.

## Camera Test

Run one-frame capture with a camera index:

```bash
source .venv/bin/activate
python raspberry_pi/camera_ai/camera_test.py --camera 0
```

Or with a Linux video device path:

```bash
source .venv/bin/activate
python raspberry_pi/camera_ai/camera_test.py --device /dev/video0
```

For the BUFFALO BSW500M USB camera on Raspberry Pi 4B, the default profile is
set to a low-bandwidth headless profile to try first:

```text
/dev/video0, YUYV, 320x240, 5 fps
```

If the camera opens but captures no frame, try a different video node or pixel
format:

```bash
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext
python raspberry_pi/camera_ai/camera_test.py --device /dev/video1
python raspberry_pi/camera_ai/camera_test.py --device /dev/video0 --fourcc YUYV --width 320 --height 240 --fps 5
```

You can also let the test script try common USB camera settings:

```bash
python raspberry_pi/camera_ai/camera_test.py --device /dev/video0 --auto-profiles
python raspberry_pi/camera_ai/camera_test.py --device /dev/video0 --backend any --auto-profiles
```

The script prints camera properties and saves one debug image under `data/debug_frames/`.

## Run AI Detection

Use the default config:

```bash
source .venv/bin/activate
python raspberry_pi/camera_ai/run_camera_ai.py --config raspberry_pi/camera_ai/config.camera_ai.yaml
```

The default config uses `/dev/video0`, `YUYV`, `320x240`, and `5 fps` for
headless Raspberry Pi operation with the BUFFALO BSW500M camera.

Override camera and model:

```bash
source .venv/bin/activate
python raspberry_pi/camera_ai/run_camera_ai.py --camera 0 --model models/bear_yolo.pt
```

Run one inference cycle:

```bash
source .venv/bin/activate
python raspberry_pi/camera_ai/run_camera_ai.py --device /dev/video0 --once
```

For a short smoke test without running forever:

```bash
source .venv/bin/activate
python raspberry_pi/camera_ai/run_camera_ai.py --device /dev/video0 --max-iterations 5
```

## Output

The module emits JSON Lines:

```json
{"timestamp":"2026-06-07T12:00:00+09:00","source":"camera_ai","camera_device":"/dev/video0","ai_camera_ok":true,"ai_model_ok":true,"ai_bear_detected":true,"ai_bear_confidence":0.82,"ai_bear_box_area_ratio":0.18,"ai_bear_approaching":true,"event":"AI_BEAR_APPROACHING","inference_time_ms":120.5}
```

If the camera, model, or runtime fails, the output is fail-safe:

```text
ai_bear_approaching=false
```

CSV logs are saved separately from contact-pad logs at `data/logs/camera_ai_log.csv` by default.

## Approach Logic

`ai_bear_approaching` becomes true only when all configured conditions are satisfied:

- target class matches, default `bear`
- confidence is at least `confidence_threshold`
- bounding-box area ratio is at least `approach_area_ratio_threshold`
- the condition is true for `consecutive_required` checks

The camera AI module does not command honey release. A future integration must still require contact confirmation, honey availability, system safety, and no emergency stop before any release request.

## Known Limitations

- A YOLO model is not included in Git.
- Raspberry Pi 4B should use small/nano models and low input sizes such as 320.
- Camera detection can be wrong; it is only a support signal.
- Current integration publishes AI state only and does not modify the Arduino release decision.

## Troubleshooting

### `externally-managed-environment`

Use the project virtual environment instead of system Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r raspberry_pi/camera_ai/requirements.txt
```

### `manpath: can't set the locale`

This warning is not usually related to camera capture, but you can clean it up
with:

```bash
sudo raspi-config
```

Then choose `Localisation Options` and generate/select the locale you use, such
as `en_US.UTF-8` or `ja_JP.UTF-8`.

### `ImportError: libGL.so.1`

Install the OpenCV runtime library:

```bash
sudo apt install -y libgl1
```

### `ERROR: camera could not be opened`

Check the camera device and permissions:

```bash
lsusb
ls /dev/video*
v4l2-ctl --list-devices
groups
```

Try another device path such as `/dev/video1` if multiple video devices are
shown.

### `ERROR: camera opened but no frame was captured`

The device node exists, but OpenCV did not receive an image frame. Check which
video node exposes capture frames and which pixel formats it supports:

```bash
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --all
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

Then try the most likely alternatives:

```bash
python raspberry_pi/camera_ai/camera_test.py --device /dev/video0 --auto-profiles
python raspberry_pi/camera_ai/camera_test.py --device /dev/video0 --backend any --auto-profiles
python raspberry_pi/camera_ai/camera_test.py --device /dev/video1
python raspberry_pi/camera_ai/camera_test.py --device /dev/video0 --fourcc YUYV
python raspberry_pi/camera_ai/camera_test.py --device /dev/video0 --width 320 --height 240
```

If OpenCV still captures no frame, check whether V4L2 itself can stream from the
USB camera. For the camera shown as `USB 2.0 Camera`, `/dev/video0` is usually
the capture node and `/dev/video1` may be a metadata node.

```bash
v4l2-ctl --device=/dev/video0 --stream-mmap --stream-count=10 --stream-to=/tmp/camera-test.raw
ls -lh /tmp/camera-test.raw
```

If `/tmp/camera-test.raw` is created and has a non-zero size, the camera and
kernel driver are working and the issue is likely OpenCV/backend related.

### `VIDIOC_STREAMON returned -1 (Protocol error)`

This means V4L2 itself could not start streaming from the USB camera, so the
problem is below Python/OpenCV. Check for device busy, USB/power problems, and
kernel driver errors:

```bash
fuser -v /dev/video0
dmesg -T | grep -iE "usb|uvc|video|camera|error|fail|protocol" | tail -80
vcgencmd get_throttled
```

Then unplug and replug the USB camera, or try another Raspberry Pi USB port. If
the camera is connected through a hub, try connecting it directly or using a
powered hub.

Try forcing a supported capture format before streaming:

```bash
v4l2-ctl --device=/dev/video0 \
  --set-fmt-video=width=640,height=480,pixelformat=MJPG \
  --stream-mmap --stream-count=10 --stream-to=/tmp/camera-test.raw

v4l2-ctl --device=/dev/video0 \
  --set-fmt-video=width=640,height=480,pixelformat=YUYV \
  --stream-mmap --stream-count=10 --stream-to=/tmp/camera-test-yuyv.raw
```

You can also test with a simple camera utility:

```bash
sudo apt install -y fswebcam
fswebcam -d /dev/video0 -r 640x480 --jpeg 85 /tmp/fswebcam.jpg
ls -lh /tmp/fswebcam.jpg
```

If V4L2 and `fswebcam` both fail, replace the USB cable/camera or test the same
camera on another computer before debugging the Python code further.

Recommended next checks:

```bash
sudo reboot
```

After reboot, unplug and replug the USB camera, then try:

```bash
lsusb -t
v4l2-ctl --device=/dev/video0 \
  --set-fmt-video=width=320,height=240,pixelformat=MJPG \
  --stream-mmap --stream-count=10 --stream-to=/tmp/camera-test-320.raw
```

If it still fails, reload the UVC driver once and retry:

```bash
fuser -v /dev/video0 /dev/video1
sudo modprobe -r uvcvideo
sudo modprobe uvcvideo
v4l2-ctl --device=/dev/video0 \
  --set-fmt-video=width=320,height=240,pixelformat=MJPG \
  --stream-mmap --stream-count=10 --stream-to=/tmp/camera-test-320.raw
```

Some non-compliant UVC cameras need a bandwidth quirk:

```bash
fuser -v /dev/video0 /dev/video1
sudo modprobe -r uvcvideo
sudo modprobe uvcvideo quirks=0x80
v4l2-ctl --device=/dev/video0 \
  --set-fmt-video=width=320,height=240,pixelformat=MJPG \
  --stream-mmap --stream-count=10 --stream-to=/tmp/camera-test-320.raw
```

If the quirk fixes the camera, make it persistent:

```bash
echo 'options uvcvideo quirks=0x80' | sudo tee /etc/modprobe.d/uvcvideo.conf
```

If `modprobe: FATAL: Module uvcvideo is in use` appears, first find and stop
users of the video devices:

```bash
fuser -v /dev/video0 /dev/video1
fuser -v /dev/snd/*
```

If no user process is shown, unload dependent camera/audio modules in this
order, then load `uvcvideo` again:

```bash
sudo modprobe -r snd-usb-audio
sudo modprobe -r uvcvideo
sudo modprobe uvcvideo quirks=0x80
sudo modprobe snd-usb-audio
```

On desktop Raspberry Pi OS, audio services may keep `snd-usb-audio` busy. If
needed, stop them temporarily before unloading the modules:

```bash
systemctl --user stop pipewire pipewire-pulse wireplumber pulseaudio 2>/dev/null || true
sudo modprobe -r snd-usb-audio
sudo modprobe -r uvcvideo
sudo modprobe uvcvideo quirks=0x80
sudo modprobe snd-usb-audio
```

If the module still cannot be unloaded, use the persistent quirk route and
reboot. This is often simpler than fighting modules that are already in use:

```bash
echo 'options uvcvideo quirks=0x80' | sudo tee /etc/modprobe.d/uvcvideo.conf
sudo reboot
```

After reboot, reconnect the camera and test before opening any camera app:

```bash
v4l2-ctl --device=/dev/video0 \
  --set-fmt-video=width=320,height=240,pixelformat=MJPG \
  --stream-mmap --stream-count=10 --stream-to=/tmp/camera-test-320.raw
ls -lh /tmp/camera-test-320.raw
```

### `AI_MODEL_LOAD_ERROR`

Check that the model file exists at the configured path:

```bash
ls -lh models/yolo_bear.pt
```

Or pass the model path explicitly:

```bash
python raspberry_pi/camera_ai/run_camera_ai.py --model models/bear_yolo.pt --once
```
