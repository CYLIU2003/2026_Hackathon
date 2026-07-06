from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import numpy as np


class YoloBearDetector:
    """Small YOLO wrapper that returns plain detection dictionaries.

    Supports three backends:

    * **NCNN** (primary) — for ``models/yolo_bear_ncnn_model/`` directories.
      Uses ``ncnn`` package.  No PyTorch / ultralytics required.
    * **ONNX Runtime** — for ``.onnx`` files, including opset 18 exports.
      Uses ``onnxruntime`` plus OpenCV image preprocessing.
    * **Ultralytics** (fallback) — for ``.pt`` files.  Requires
      ``ultralytics`` and PyTorch.
    """

    def __init__(
        self,
        model_path: str | Path,
        *,
        input_size: int = 256,
        confidence_floor: float = 0.05,
        device: str | None = "cpu",
        class_ids: list[int] | tuple[int, ...] | None = None,
        enable_model_fusion: bool = True,
    ):
        self.model_path = str(model_path)
        self.input_size = int(input_size)
        self.confidence_floor = float(confidence_floor)
        self.device = device
        self.class_ids = tuple(int(class_id) for class_id in (class_ids or ()))
        if self.input_size <= 0:
            raise RuntimeError("YOLO input_size must be a positive integer.")
        if not Path(self.model_path).exists():
            raise RuntimeError(
                f"YOLO model file is missing: {self.model_path}. "
                "Place an exported runtime model at models/yolo_bear.onnx or "
                "models/yolo_bear_ncnn_model, or use a development-only fallback "
                "prototype model at models/yolo_bear.pt."
            )

        self._backend: str  # "ncnn" | "onnxruntime" | "ultralytics"
        self._class_names: dict[int, str] = {}

        self._check_runtime_dependency()
        if self._is_ncnn_model(self.model_path):
            self._init_ncnn()
        elif self._is_onnx_model(self.model_path):
            self._init_onnx()
        else:
            self._init_ultralytics(enable_model_fusion)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def detect(self, frame: Any) -> list[dict]:
        """Run object detection on *frame* (BGR numpy array).

        Returns a list of detection dicts sorted by confidence descending.
        """
        if self._backend == "ncnn":
            return self._detect_ncnn(frame)
        if self._backend == "onnxruntime":
            return self._detect_onnx(frame)
        return self._detect_ultralytics(frame)

    # ------------------------------------------------------------------
    # backend detection
    # ------------------------------------------------------------------

    @staticmethod
    def _is_ncnn_model(model_path: str) -> bool:
        p = Path(model_path)
        return p.is_dir() and any(p.glob("*.ncnn.param"))

    @staticmethod
    def _is_onnx_model(model_path: str) -> bool:
        return Path(model_path).suffix.lower() == ".onnx" and Path(model_path).is_file()

    def _check_runtime_dependency(self) -> None:
        """Fail early with backend-specific install guidance."""
        if self._is_ncnn_model(self.model_path):
            if importlib.util.find_spec("ncnn") is None:
                raise RuntimeError(
                    "NCNN runtime is not installed. Install "
                    "raspberry_pi/camera_ai/requirements.txt on the Raspberry Pi "
                    "or place an ONNX model at models/yolo_bear.onnx."
                )
            return
        if self._is_onnx_model(self.model_path):
            if importlib.util.find_spec("cv2") is None:
                raise RuntimeError(
                    "OpenCV (cv2) is not installed. Install "
                    "raspberry_pi/camera_ai/requirements.txt to use the ONNX backend."
                )
            if importlib.util.find_spec("onnxruntime") is None:
                raise RuntimeError(
                    "ONNX Runtime is not installed. Install "
                    "raspberry_pi/camera_ai/requirements.txt to use opset 18 "
                    "ONNX models such as models/yolo_bear.onnx."
                )
            return
        if importlib.util.find_spec("ultralytics") is None:
            raise RuntimeError(
                "ultralytics is not installed. It is only required for .pt fallback "
                "models and export work. Prefer models/yolo_bear.onnx or "
                "models/yolo_bear_ncnn_model on Raspberry Pi, or install "
                "raspberry_pi/camera_ai/requirements.export.txt in a Colab/development "
                "environment."
            )

    # ------------------------------------------------------------------
    # NCNN backend
    # ------------------------------------------------------------------

    def _init_ncnn(self) -> None:
        import ncnn

        model_dir = Path(self.model_path)
        param_files = sorted(model_dir.glob("*.ncnn.param"))
        bin_files = sorted(model_dir.glob("*.ncnn.bin"))
        if not param_files or not bin_files:
            raise RuntimeError(f"NCNN model files missing in {self.model_path}")

        self._ncnn_net = ncnn.Net()
        # Pi/aarch64 で segfault しにくいよう、軽量な設定を明示。
        # 利用可能な setter だけを try で包み、存在しなくても継続する。
        for option_name, args in (
            ("set_num_threads", (1,)),
            ("set_light_mode", (True,)),
            ("set_fp16_packed", (False,)),
            ("set_fp16_storage", (False,)),
            ("set_fp16_arithmetic", (False,)),
            ("set_bf16s_packed", (False,)),
            ("set_bf16s_storage", (False,)),
            ("set_bf16s_arithmetic", (False,)),
            ("set_use_packing_layout", (0,)),
            ("set_vulkan_compute", (False,)),
        ):
            setter = getattr(self._ncnn_net, option_name, None)
            if setter is None:
                continue
            try:
                setter(*args)
            except Exception:
                pass
        ret = self._ncnn_net.load_param(str(param_files[0]))
        if ret != 0:
            raise RuntimeError(f"Failed to load NCNN param: {param_files[0]}")
        ret = self._ncnn_net.load_model(str(bin_files[0]))
        if ret != 0:
            raise RuntimeError(f"Failed to load NCNN bin: {bin_files[0]}")

        # Load class names from metadata.yaml
        metadata_path = model_dir / "metadata.yaml"
        if metadata_path.exists():
            self._class_names = self._load_metadata_class_names(metadata_path)
        else:
            self._class_names = {0: "bear"}

        self._backend = "ncnn"

    def _detect_ncnn(self, frame: Any) -> list[dict]:
        import ncnn

        frame_height, frame_width = frame.shape[:2]
        frame_area = max(1, int(frame_width) * int(frame_height))

        # Preprocess: resize & normalize
        mat = ncnn.Mat.from_pixels_resize(
            frame.tobytes(),
            ncnn.Mat.PixelType.PIXEL_BGR2RGB,
            frame_width,
            frame_height,
            self.input_size,
            self.input_size,
        )
        mat.substract_mean_normalize([0, 0, 0], [1 / 255.0, 1 / 255.0, 1 / 255.0])

        # Inference
        ex = self._ncnn_net.create_extractor()
        ex.input("in0", mat)
        _, out_mat = ex.extract("out0")
        out = np.array(out_mat)  # shape: (5, N)

        # Parse detections
        detections: list[dict] = []
        scale_x = frame_width / self.input_size
        scale_y = frame_height / self.input_size

        for i in range(out.shape[1]):
            cx, cy, bw, bh, conf = out[:, i]
            conf = float(conf)
            if conf < self.confidence_floor:
                continue

            # Convert center coords → xyxy in model space, then scale to frame
            x1 = float((cx - bw / 2.0) * scale_x)
            y1 = float((cy - bh / 2.0) * scale_y)
            x2 = float((cx + bw / 2.0) * scale_x)
            y2 = float((cy + bh / 2.0) * scale_y)

            # Clamp to frame bounds
            x1 = max(0.0, min(x1, frame_width))
            y1 = max(0.0, min(y1, frame_height))
            x2 = max(0.0, min(x2, frame_width))
            y2 = max(0.0, min(y2, frame_height))

            box_area_ratio = self._box_area_ratio([x1, y1, x2, y2], frame_area)
            class_index = 0  # single-class model
            class_name = self._class_names.get(class_index, str(class_index)).lower()

            # Filter by class_ids if specified
            if self.class_ids and class_index not in self.class_ids:
                continue

            detections.append(
                {
                    "class_name": class_name,
                    "confidence": conf,
                    "bbox_xyxy": [x1, y1, x2, y2],
                    "box_area_ratio": box_area_ratio,
                }
            )

        return sorted(
            detections,
            key=lambda d: float(d["confidence"]),
            reverse=True,
        )

    @staticmethod
    def _load_metadata_class_names(metadata_path: Path) -> dict[int, str]:
        try:
            import yaml
        except ImportError:
            return {0: "bear"}
        with metadata_path.open("r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
        names = meta.get("names", {0: "bear"})
        return {int(k): str(v) for k, v in names.items()}

    # ------------------------------------------------------------------
    # ONNX Runtime backend — no PyTorch / ultralytics required
    # ------------------------------------------------------------------

    def _init_onnx(self) -> None:
        try:
            import cv2
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError(
                "OpenCV (cv2) and ONNX Runtime are required for the ONNX backend. "
                "Install raspberry_pi/camera_ai/requirements.txt on the Raspberry Pi."
            ) from exc

        try:
            ort.set_default_logger_severity(3)
        except Exception:
            pass
        self._cv2 = cv2
        session_options = ort.SessionOptions()
        session_options.intra_op_num_threads = 1
        session_options.inter_op_num_threads = 1
        session_options.log_severity_level = 3
        self._onnx_session = ort.InferenceSession(
            self.model_path,
            sess_options=session_options,
            providers=["CPUExecutionProvider"],
        )
        model_inputs = self._onnx_session.get_inputs()
        if not model_inputs:
            raise RuntimeError(f"ONNX model has no inputs: {self.model_path}")
        self._onnx_input_name = model_inputs[0].name
        self._onnx_output_names = [
            output.name for output in self._onnx_session.get_outputs()
        ]
        input_shape = list(getattr(model_inputs[0], "shape", []) or [])
        if (
            len(input_shape) == 4
            and isinstance(input_shape[2], int)
            and isinstance(input_shape[3], int)
            and input_shape[2] > 0
            and input_shape[2] == input_shape[3]
        ):
            self.input_size = int(input_shape[2])

        # Load class names from sibling metadata.yaml if present.
        model_file = Path(self.model_path)
        metadata_path = model_file.parent / "metadata.yaml"
        if metadata_path.exists():
            self._class_names = self._load_metadata_class_names(metadata_path)
        else:
            self._class_names = {0: "bear"}

        self._backend = "onnxruntime"

    def _detect_onnx(self, frame: Any) -> list[dict]:
        cv2 = self._cv2
        frame_height, frame_width = frame.shape[:2]
        frame_area = max(1, int(frame_width) * int(frame_height))

        # Preprocess: letterbox-free simple resize + normalize (0..1).
        resized = cv2.resize(frame, (self.input_size, self.input_size))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        input_tensor = np.ascontiguousarray(
            rgb.transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        )
        outputs = self._onnx_session.run(
            self._onnx_output_names,
            {self._onnx_input_name: input_tensor},
        )
        if not outputs:
            return []
        out = outputs[0]

        # Ultralytics YOLOv8 ONNX output layout: [1, 4+nc, num_anchors] with
        # rows [cx, cy, w, h, cls0_score, cls1_score, ...] and NO objectness.
        # Rearrange to (num_anchors, 4+nc).
        if out.ndim == 3:
            out = out[0]
        if out.shape[0] < out.shape[-1]:
            out = out.T
        detections: list[dict] = []
        scale_x = frame_width / self.input_size
        scale_y = frame_height / self.input_size
        for row in out:
            if row.shape[0] < 5:
                continue
            class_scores = row[4:]
            class_index = int(np.argmax(class_scores))
            conf = float(class_scores[class_index])
            if conf < self.confidence_floor:
                continue
            if self.class_ids and class_index not in self.class_ids:
                continue
            cx, cy, bw, bh = [float(v) for v in row[:4]]
            # Coordinates are in input_size space; rescale to frame size.
            scale_x = frame_width / self.input_size
            scale_y = frame_height / self.input_size
            x1 = max(0.0, (cx - bw / 2.0) * scale_x)
            y1 = max(0.0, (cy - bh / 2.0) * scale_y)
            x2 = min(float(frame_width), (cx + bw / 2.0) * scale_x)
            y2 = min(float(frame_height), (cy + bh / 2.0) * scale_y)
            box_area_ratio = self._box_area_ratio([x1, y1, x2, y2], frame_area)
            class_name = self._class_names.get(class_index, str(class_index)).lower()
            detections.append(
                {
                    "class_name": class_name,
                    "confidence": conf,
                    "bbox_xyxy": [x1, y1, x2, y2],
                    "box_area_ratio": box_area_ratio,
                }
            )
        return sorted(
            detections,
            key=lambda detection: float(detection["confidence"]),
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Ultralytics (PyTorch) fallback backend
    # ------------------------------------------------------------------

    def _init_ultralytics(self, enable_model_fusion: bool) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "ultralytics is not installed. Install "
                "raspberry_pi/camera_ai/requirements.export.txt in a Colab/development "
                "environment, or use models/yolo_bear.onnx / "
                "models/yolo_bear_ncnn_model on Raspberry Pi."
            ) from exc

        try:
            self.model = YOLO(self.model_path, task="detect")
        except Exception as exc:
            raise RuntimeError(f"failed to load YOLO model: {self.model_path}") from exc
        self._backend = "ultralytics"
        self._class_names = dict(self.model.names)
        if enable_model_fusion:
            self._try_fuse_model()

    def _detect_ultralytics(self, frame: Any) -> list[dict]:
        frame_height, frame_width = frame.shape[:2]
        frame_area = max(1, int(frame_width) * int(frame_height))
        predict_kwargs: dict = {
            "imgsz": self.input_size,
            "conf": self.confidence_floor,
            "verbose": False,
        }
        if self.device:
            predict_kwargs["device"] = self.device
        if self.class_ids:
            predict_kwargs["classes"] = list(self.class_ids)
        results = self.model.predict(frame, **predict_kwargs)

        detections: list[dict] = []
        for result in results:
            names = result.names
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            for box in boxes:
                xyxy = [float(value) for value in box.xyxy[0].cpu().tolist()]
                confidence = float(box.conf[0].cpu().item())
                class_index = int(box.cls[0].cpu().item())
                class_name = str(names.get(class_index, class_index)).lower()
                box_area_ratio = self._box_area_ratio(xyxy, frame_area)
                detections.append(
                    {
                        "class_name": class_name,
                        "confidence": confidence,
                        "bbox_xyxy": xyxy,
                        "box_area_ratio": box_area_ratio,
                    }
                )

        return sorted(
            detections,
            key=lambda detection: float(detection["confidence"]),
            reverse=True,
        )

    def _try_fuse_model(self) -> None:
        fuse = getattr(self.model, "fuse", None)
        if not callable(fuse):
            return
        try:
            fuse()
        except Exception:
            return

    # ------------------------------------------------------------------
    # shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _box_area_ratio(bbox_xyxy: list[float], frame_area: int) -> float:
        x1, y1, x2, y2 = bbox_xyxy
        width = max(0.0, x2 - x1)
        height = max(0.0, y2 - y1)
        return min(1.0, (width * height) / float(frame_area))
