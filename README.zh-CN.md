# A1 前掌接触垫系统 / Front Paw Contact Pad System

## 概要

本仓库用于 A1 **Bear Honey Buffet** 黑客松项目中的 **Front Paw Contact Pad System** 原型开发。

当前原型不仅包含模拟输入和接触垫控制，还包含 Raspberry Pi 侧的相机AI识别模块。系统会检测熊或目标物是否接近，确认前掌接触或未来的电阻/接触垫输入，检查蜂蜜余量和安全状态，然后安全地判断是否发送蜂蜜释放信号。

相机AI是额外的感知层，不是唯一的安全控制器。不能只因为YOLO检测到熊就释放蜂蜜。

控制逻辑的初始版本仍然可以只使用 **模拟传感器输入** 运行。传统的Arduino/接触垫和电阻接触确认路径必须保留在仓库中，并在之后单独集成。

---

## 项目愿景

A1系统整体分为四个层。

```text
[Bear]
  ↓
[Camera AI perception layer]
  ↓ ai_bear_approaching
[Contact / resistance confirmation layer]
  ↓ paw_contact / raw_contact_value
[Safety decision layer]
  ↓ RELEASE_ON / RELEASE_OFF
[Honey release actuator layer]
  ↓
[Honey release mechanism]
```

本仓库负责感知、接触确认、安全判断逻辑、日志记录和演示支持。蜂蜜释放驱动侧以简单的 RELEASE_ON/OFF 接口表示，之后再集成 PCA9685 + 舵机。

---

## 本系统要做什么

系统会判断以下内容。

```text
1. 熊或目标物是否接近              ai_bear_approaching / bear_detected
2. 前掌是否接触接触垫              paw_contact / raw_contact_value
3. 蜂蜜剩余量是否足够              honey_amount_percent
4. 系统是否处于安全状态            system_safe
5. 紧急停止是否未触发              emergency_stop == false
6. 是否可以启动蜂蜜释放机构        RELEASE_ON / RELEASE_OFF
```

如果所有条件都满足，系统输出：

```text
RELEASE_ON
```

如果任意条件不满足，系统输出：

```text
RELEASE_OFF
```

---

## 硬件概念

### Arduino Uno Q

Arduino Uno Q 继续作为现场侧接触确认和安全控制板。

主要职责：

```text
- 接触垫输入
- 未来的电阻/接触测量
- 模拟传感器输入
- 阈值判断
- 蜂蜜释放判定逻辑
- LED / GPIO / release signal 输出
- serial 或 network 通信
```

Arduino Uno Q / 电阻测量 / 接触垫逻辑必须继续保留在文档和实现中。camera AI 可以增加 `ai_bear_approaching`，但不能替代 `paw_contact`、`raw_contact_value`、接触阈值、紧急停止和 RELEASE_OFF 故障安全行为。

Arduino Uno Q 同时具有可运行Linux的MPU侧和实时控制用MCU侧，因此适合承担现场控制任务。

参考：

```text
https://docs.arduino.cc/hardware/uno-q
https://docs.arduino.cc/tutorials/uno-q/user-manual/
```

### Raspberry Pi 4B

Raspberry Pi 4B 4GB 用于AI相机识别、日志记录和上位状态处理。

主要职责：

```text
- 从 BUFFALO BSW500M USB摄像头获取图像
- 使用 OpenCV / V4L2 进行相机采集
- 使用轻量YOLO进行熊接近检测
- 输出 ai_bear_approaching 状态
- 接收 Arduino Uno Q 的状态数据
- 保存CSV日志
- 显示仪表盘
- 可视化最新状态
- 支持演示和发表
- 通过 SSH / Tailscale 进行远程访问
```

Raspberry Pi 不应作为唯一的安全控制器。相机AI是额外的感知层，不是唯一的安全控制器。

### BUFFALO BSW500M USB摄像头

BUFFALO BSW500M USB Web摄像头连接到 Raspberry Pi 4B。

```text
- USB ID: 0411:02da
- /dev/video0: 实际图像流设备
- /dev/video1: metadata device，不能用于图像采集
- 默认配置: device=auto，会优先选择 0411:02da 的 Video Capture 节点并跳过 metadata 节点
- 推荐FourCC: 先MJPG，失败时fallback到YUYV
- 推荐分辨率: 先640x480，失败时fallback到320x240
```

### PCA9685 + 舵机

PCA9685 + 舵机 + 外部电源用于蜂蜜释放机构侧的驱动。

```text
- 输入: RELEASE_ON / RELEASE_OFF
- 作用: 驱动演示用蜂蜜释放机构
- 安全: 禁止无控制释放；默认状态必须是 RELEASE_OFF
```

---

## 系统架构

```text
Bear / target object
  ↓
BUFFALO BSW500M USB Camera
  ↓
Raspberry Pi 4B 4GB
  - OpenCV / V4L2 camera capture
  - YOLO bear detection
  - bear approach judgement
  - JSON Lines / CSV logging
  ↓
Existing decision logic
  - ai_bear_approaching
  - paw_contact / resistance measurement
  - honey_amount_percent
  - system_safe
  - emergency_stop
  ↓
RELEASE_ON / RELEASE_OFF
  ↓
PCA9685 + Servo Motor
  ↓
Honey release mechanism
```

---

## MVP v0.1

第一个MVP需要实现以下内容。

### 输入

```text
simulated_bear_detected
ai_bear_approaching
simulated_paw_contact
raw_contact_value
simulated_honey_amount_percent
simulated_system_safe
emergency_stop
```

### 控制逻辑

```text
release_allowed = (
    ai_bear_approaching
    and paw_contact
    and honey_amount_percent >= honey_min_threshold_percent
    and system_safe
    and not emergency_stop
)
```

### 输出

```text
- RELEASE_ON / RELEASE_OFF
- LED ON/OFF
- JSON Lines over serial
- CSV log on Raspberry Pi
- Camera AI JSON Lines / CSV state
```

---

## 状态机

```text
IDLE
  ↓ bear detected
BEAR_DETECTED
  ↓ paw contact confirmed
CONTACT_CONFIRMED
  ↓ honey enough and system safe
READY_TO_RELEASE
  ↓ release command
RELEASING
  ↓ timeout
COOLDOWN
  ↓ cooldown finished
IDLE
```

异常时：

```text
ANY_STATE
  ↓ invalid data / emergency stop / communication error
ERROR_SAFE
  ↓ reset
IDLE
```

在 `ERROR_SAFE` 状态下，必须始终保持 `RELEASE_OFF`。

---

## 安全策略

本项目是黑客松原型，不得伤害人或动物。

禁止事项：

```text
- 在接触垫上使用高电压或大电流
- 设计电击装置
- 在没有专家监督的情况下使用真实熊进行测试
- 在没有有效测量的情况下声称得到了真实熊的电阻数据
- 在没有安全停止机制的情况下控制蜂蜜释放
```

必须遵守：

```text
- 初始状态和异常状态必须是 RELEASE_OFF
- 在没有真实传感器时使用模拟输入
- 相机AI是额外的感知层，不是唯一的安全控制器
- 不能只靠YOLO检测触发蜂蜜释放
- RELEASE_ON 必须有时间限制
- 重要状态变化必须记录日志
- 接触垫控制系统与蜂巢机械结构必须分离
```

只有在所有必要条件都满足时，才允许释放蜂蜜。

```python
release_allowed = (
    ai_bear_approaching
    and paw_contact
    and honey_amount_percent >= honey_min_threshold_percent
    and system_safe
    and not emergency_stop
)
```

---

## 数据格式

Arduino Uno Q 向 Raspberry Pi 发送 JSON Lines。

示例：

```json
{"timestamp":"2026-05-23T18:30:00+09:00","bear_detected":false,"paw_contact":false,"honey_amount_percent":80,"system_safe":true,"emergency_stop":false,"release_state":"RELEASE_OFF","state":"IDLE","event":"IDLE"}
{"timestamp":"2026-05-23T18:30:05+09:00","bear_detected":true,"paw_contact":true,"honey_amount_percent":80,"system_safe":true,"emergency_stop":false,"release_state":"RELEASE_ON","state":"RELEASING","event":"RELEASE_START"}
```

Raspberry Pi 侧保存CSV日志。

示例：

```csv
timestamp,bear_detected,paw_contact,honey_amount_percent,system_safe,emergency_stop,release_state,state,event
2026-05-23T18:30:00+09:00,false,false,80,true,false,RELEASE_OFF,IDLE,IDLE
2026-05-23T18:30:05+09:00,true,true,80,true,false,RELEASE_ON,RELEASING,RELEASE_START
```

Camera AI 也会从 Raspberry Pi 输出 JSON Lines。

```json
{"source":"camera_ai","ai_camera_ok":true,"ai_model_ok":true,"ai_bear_detected":true,"ai_bear_confidence":0.82,"ai_bear_box_area_ratio":0.18,"ai_bear_approaching":true,"event":"AI_BEAR_APPROACHING"}
```

这些 camera AI 字段只是安全判断层的输入，不会直接命令 `RELEASE_ON`。

---

## 推荐仓库结构

```text
a1-front-paw-contact-pad/
├─ README.md
├─ README.ja.md
├─ README.zh-CN.md
├─ README.ko.md
├─ AI_DEVELOPMENT_INSTRUCTIONS.md
├─ VARIABLES.md
├─ PROJECT_GUARDRAILS.md
├─ docs/
│  ├─ block_diagram.md
│  ├─ state_machine.md
│  ├─ interface_spec.md
│  ├─ camera_ai_design.md
│  └─ camera_ai_interface_spec.md
├─ arduino_uno_q/
│  ├─ contact_pad_controller/
│  │  ├─ contact_pad_controller.ino
│  │  └─ config.h
│  └─ README.md
├─ raspberry_pi/
│  ├─ camera_ai/
│  │  ├─ run_camera_ai.py
│  │  ├─ camera_test.py
│  │  ├─ camera_capture.py
│  │  ├─ bear_detector.py
│  │  ├─ approach_logic.py
│  │  └─ config.camera_ai.yaml
│  ├─ logger/
│  │  ├─ serial_logger.py
│  │  └─ requirements.txt
│  ├─ dashboard/
│  │  ├─ app.py
│  │  └─ requirements.txt
│  └─ README.md
├─ data/
│  └─ logs/
├─ models/
│  └─ yolo_bear.pt
├─ outputs/
│  └─ camera_test.jpg
├─ examples/
│  └─ sample_log.csv
└─ scripts/
   └─ run_demo.sh
```

---

`models/` 和 `outputs/` 是运行时和演示时使用的目录。
模型权重和相机输出图像通常不提交到Git，除非团队明确决定保留小型示例文件。

---

## Camera AI 模块

Camera AI 模块运行在 Raspberry Pi 4B 4GB 上，使用 BUFFALO BSW500M USB Web摄像头。

相机AI是额外的感知层，不是唯一的安全控制器。
远程浏览器画面只用于监控和演示支持，不会把 RELEASE_ON/OFF 的安全判断从
Arduino/contact-pad 侧移到 Raspberry Pi。

硬件和运行时前提：

```text
- 目标设备: Raspberry Pi 4B 4GB
- 摄像头: BUFFALO BSW500M USB Web摄像头
- USB ID: 0411:02da
- 图像采集设备: device=auto，目标Pi上会解析为 /dev/video0
- metadata device: /dev/video1，不能用于采集
- 优先模型路径: models/yolo_bear_ncnn_model
- fallback模型路径: models/yolo_bear.pt
- Raspberry Pi 4B 推荐分辨率: 320x240
- 推荐FourCC: 先MJPG，失败时fallback到YUYV
- 失败行为: ai_bear_approaching=false
```

如果所有配置的模型路径都缺失，系统输出 `AI_MODEL_LOAD_ERROR`，设置 `ai_model_ok=false`，并保持故障安全状态。

远程监控的工作方式：

```text
Camera AI process
  -> 保存CSV: data/logs/camera_ai_log.csv
  -> 保存最新标注图像: data/debug_frames/latest_camera_ai.jpg
Dashboard process
  -> 浏览器页面: http://<pi-ip>:8080
  -> 最新图像: /camera/latest.jpg
```

在 Raspberry Pi bring-up 检查中，`.pt` 的 PyTorch fallback 在
`YOLO.predict()` 时出现 `Illegal instruction`。安装 `ncnn` 并使用
`models/yolo_bear_ncnn_model` 后，启动和推理都可以通过。因此 Pi 演示时应把
NCNN模型作为正常运行路径。

如果当前 Pi 环境的 `ncnn` 运行时（例如 `ncnn==1.0.20260526` 的 aarch64 构建）
在 `extract("out0")` 时发生 SIGSEGV，Camera AI 会立刻崩溃，画面会停在最后一帧。
此时无需在 Pi 上安装 PyTorch，只要用 Colab 把 `.pt` 导出为 ONNX 并放置
`models/yolo_bear.onnx`，Camera AI 会自动优先使用
ONNX Runtime 推理路径（无需 NCNN/Pi 上无需安装 PyTorch 或 Ultralytics）。
因此 Raspberry Pi 运行时的 `raspberry_pi/camera_ai/requirements.txt`
包含 `onnxruntime`，但不包含 PyTorch 和 Ultralytics。只有在 Colab 或开发电脑上进行训练/导出时，
才使用 `raspberry_pi/camera_ai/requirements.export.txt`。

ONNX 导出流程（在 Colab 上执行，Pi 只需要 runtime requirements）：

```text
1. 打开 notebooks/export_bear_yolo_onnx.ipynb
2. 上传仓库的 best.pt
3. 运行全部 cell，导出 models/yolo_bear.onnx（imgsz=256, opset 18；仅转换成功时为 opset 12）
4. 下载 yolo_bear.onnx，放置到 Pi 的 models/yolo_bear.onnx
5. 在 Pi 上重新运行 ./scripts/run_demo.sh
6. 确认 ai_model_ok=true 且画面持续更新
```

当 `models/yolo_bear.onnx` 存在时，`scripts/run_demo.sh` 默认会启用推理
（`RUN_CAMERA_AI_INFERENCE` 自动为 1）。没有 ONNX 时默认进入相机仅
故障安全模式（`ai_model_ok=false`、保持 HOLD、画面仍持续更新）。
`scripts/run_demo.sh` 的默认 `CAMERA_DEVICE=auto`，会在启动时选择
BUFFALO BSW500M 的 Video Capture 节点；如果现场需要固定设备，也可以使用
`CAMERA_DEVICE=/dev/video0 ./scripts/run_demo.sh`。

Camera AI 运行命令：

```bash
python3 -m compileall -q raspberry_pi/camera_ai
python3 raspberry_pi/camera_ai/camera_test.py --device auto
python3 -m raspberry_pi.camera_ai.run_camera_ai --terminal-status --no-jsonl --once
```

摄像头调试命令：

```bash
lsusb
ls /dev/video*
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext
fuser -v /dev/video0
```

---

## 各目录职责

| 路径 | 职责 |
|---|---|
| `arduino_uno_q/contact_pad_controller/` | Arduino Uno Q 主控制。负责模拟输入、接触垫状态机、蜂蜜量阈值判断、RELEASE_ON/OFF输出、LED/GPIO、JSON Lines输出。 |
| `raspberry_pi/logger/` | Raspberry Pi 串口日志程序。接收Arduino和AI的JSON Lines并保存为CSV日志。 |
| `raspberry_pi/dashboard/` | 演示和监控用仪表盘。统一显示接触状态、AI状态和释放状态。 |
| `raspberry_pi/camera_ai/` | 可选的相机AI感知层。负责测试 `/dev/video0`、加载YOLO、估计熊是否接近、输出AI状态。但不能直接命令蜂蜜释放。 |
| `docs/` | 设计资料，包括框图、状态机、接口规格和camera AI设计说明。 |
| `data/logs/` | 运行时CSV/JSONL日志目录。除小型示例外，生成日志通常不提交到Git。 |
| `examples/` | 演示和说明用的小型示例输入/输出文件。 |
| `models/` | 本地YOLO模型权重和导出目录。优先路径是 `models/yolo_bear_ncnn_model`，`.pt` 只作为fallback。默认不提交到Git。 |
| `outputs/` | 相机测试图像和临时演示输出。默认不提交到Git。 |
| `scripts/` | 演示运行辅助脚本。 |
| `tests/` | 决策逻辑和camera AI辅助处理的Python测试。 |
| 根目录文件 | 项目整体说明、开发指示、安全边界、变量列表和多语言README。 |

---

## 开发路线图

### Phase 1: 模拟控制逻辑

```text
[ ] 模拟熊/接触/蜂蜜量/安全状态输入
[ ] RELEASE_ON/OFF 判断逻辑
[ ] 紧急停止和 RELEASE_OFF 故障安全
[ ] JSON Lines 输出
```

### Phase 2: Raspberry Pi 摄像头单体测试

```text
[ ] 将 BUFFALO BSW500M 连接到 Raspberry Pi 4B
[ ] 确认 /dev/video0 是图像流设备
[ ] /dev/video1 不用于图像采集
[ ] camera_test.py 成功获取一帧图像
```

### Phase 3: YOLO模型放置和AI推理

```text
[ ] 放置或导出 models/yolo_bear_ncnn_model
[ ] 确认 AI_MODEL_LOAD_ERROR 消失
[ ] 对相机图像运行YOLO推理
[ ] 以故障安全方式输出 ai_bear_approaching
```

### Phase 4: AI状态日志和仪表盘集成

```text
[ ] 记录 camera AI JSON Lines / CSV
[ ] 显示 ai_camera_ok 和 ai_model_ok
[ ] 显示 ai_bear_detected 和 ai_bear_approaching
[ ] 同时显示接触状态和释放状态
```

### Phase 5: 电阻/接触垫集成

```text
[ ] 保留 Arduino Uno Q 接触垫逻辑
[ ] 添加或验证 raw_contact_value
[ ] 添加接触阈值逻辑
[ ] 仅使用安全假物体测试
```

### Phase 6: PCA9685 / 舵机蜂蜜释放集成

```text
[ ] 连接 PCA9685 和外部舵机电源
[ ] 将 RELEASE_ON/OFF 映射为安全舵机动作
[ ] 添加释放超时和冷却时间
[ ] 确认复位或异常时默认为 RELEASE_OFF
```

### Phase 7: 带故障安全的全系统演示

```text
[ ] Camera AI 检测接近
[ ] 接触/电阻层确认 paw_contact
[ ] 蜂蜜量和安全条件通过
[ ] 紧急停止强制 RELEASE_OFF
[ ] 仅YOLO检测不会释放蜂蜜
```

---

## 向团队说明

```text
I will develop the front paw contact pad system as a separate electronic/control module.
Raspberry Pi 4B with a BUFFALO BSW500M camera will be used for YOLO-based bear approach detection, logging, and dashboard support.
Arduino Uno Q and the contact/resistance layer remain responsible for contact confirmation and fail-safe release logic.
PCA9685 and a servo motor will be used on the honey release mechanism side.
Camera AI is an additional perception layer, not the only safety controller.
```

---

## 当前假设

```text
- 蜂巢机构侧可以接收简单的 RELEASE_ON/OFF 信号
- Raspberry Pi 4B 使用 BUFFALO BSW500M 的 `device=auto` 图像采集路径；目标Pi上为 /dev/video0
- /dev/video1 是metadata，不能用于图像采集
- 物理接触/电阻集成与 camera AI 分开保留
- PCA9685 + 舵机 + 外部电源用于执行机构侧
- 不进行真实动物测试
- 本项目是黑客松用概念验证
```

---

## MVP v0.1 完成条件

```text
[ ] Uno Q 可以生成模拟输入
[ ] Uno Q 可以判断 RELEASE_ON/OFF
[ ] Raspberry Pi 可以通过 `device=auto` 从 BSW500M 采集图像
[ ] Camera AI 可以输出故障安全的 ai_bear_approaching
[ ] 通过LED或serial可以看到 RELEASE_ON/OFF
[ ] Raspberry Pi 可以接收状态数据
[ ] Raspberry Pi 可以保存CSV日志
[ ] 异常时可以回到 RELEASE_OFF
[ ] 仅YOLO检测不能触发蜂蜜释放
[ ] README解释了系统工作方式
[ ] 团队可以理解接触垫系统与蜂巢机构之间的边界
```

---

## 开始使用（MVP模拟）

本原型只使用 **模拟传感器输入** 也可以运行。即使没有真实传感器，也可以先验证控制逻辑。

### Arduino Uno Q

1. 打开 `arduino_uno_q/contact_pad_controller/contact_pad_controller.ino`。
2. 构建并上传到 Arduino Uno Q。
3. 以 **115200 baud** 打开串口监视器。
4. 确认 JSON Lines 输出。

### Raspberry Pi 日志程序

1. 安装依赖。
   ```bash
   pip install -r raspberry_pi/logger/requirements.txt
   ```
2. 运行日志程序。
   ```bash
   python raspberry_pi/logger/serial_logger.py --serial-port /dev/ttyACM0 --baudrate 115200
   ```
3. CSV日志保存在 `data/logs/`。

### Raspberry Pi Camera AI

在 Raspberry Pi 上，从仓库根目录执行：

```bash
cd ~/Desktop/2026_Hackathon
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/camera_ai/requirements.txt
python -m pip install -r raspberry_pi/dashboard/requirements.txt
```

Camera AI 运行时安装面向 ONNX/NCNN，Raspberry Pi 上有意不安装
PyTorch/Ultralytics。

正常演示启动。这个命令会同时启动 Camera AI、模拟接触垫安全判断、
统一CSV日志和远程仪表盘：

```bash
./scripts/run_demo.sh
```

会场上如需从实时摄像头推理一路跑到 Arduino 机构动作：

```bash
RUN_CAMERA_AI_INFERENCE=1 RUN_ACTUATOR_BRIDGE=1 ./scripts/run_demo.sh
```

桥接进程只会在最新安全 CSV 行为 `RELEASE_ON` 时向 Arduino 发送 `RELEASE`。
缺失、过期或错误数据会保持/发送 `STOP`。

从同一网络中的电脑、平板、手机，或通过 Tailscale 打开：

```text
http://<pi-ip>:8080
```

仪表盘会显示 Camera AI 最新识别画面、当前状态、熊检测、置信度、
接触确认、安全判断、`RELEASE/HOLD` 指令和CSV保存状态。
Camera AI 写出的图像路径是：

```text
data/debug_frames/latest_camera_ai.jpg
```

统一判断日志写入：

```text
data/logs/feeding_decision_log.csv
```

当前原型使用模拟接触传感器输入。默认值可在启动时修改：

```bash
MOCK_CONTACT=1 \
MOCK_IMPEDANCE_KOHM=92.4 \
HONEY_AMOUNT_PERCENT=80 \
./scripts/run_demo.sh
```

如果没有摄像头或只想排练完整状态迁移，可使用全模拟场景：

```bash
RUN_CAMERA_AI=0 SAFETY_INPUT_MODE=scenario ./scripts/run_demo.sh
```

Raspberry Pi 上的安全判断是发表和集成确认用的镜像，不直接驱动实际舵机。
实际 `RELEASE_ON / RELEASE_OFF` 的主安全控制仍由 Arduino Uno Q 承担。

只启动 Camera AI，不启动仪表盘：

```bash
python -m raspberry_pi.camera_ai.run_camera_ai \
  --device auto \
  --terminal-status \
  --no-jsonl \
  --save-debug-frames
```

只运行一次的 smoke test：

```bash
python -m raspberry_pi.camera_ai.run_camera_ai \
  --device auto \
  --terminal-status \
  --no-jsonl \
  --once \
  --save-debug-frames
```

摄像头单体确认：

```bash
python3 raspberry_pi/camera_ai/camera_test.py --device auto
```

### Raspberry Pi 仪表盘

只有在 Camera AI 已经运行并写出 `data/debug_frames/latest_camera_ai.jpg` 时，
才单独启动仪表盘：

```bash
python raspberry_pi/dashboard/app.py \
  --log-dir data/logs \
  --log-file data/logs/feeding_decision_log.csv \
  --camera-log-file data/logs/camera_ai_log.csv \
  --debug-frame-dir data/debug_frames \
  --host 0.0.0.0 \
  --port 8080
```

打开：

```text
http://<pi-ip>:8080
```

完整演示时，如果还要同时启动 Arduino Uno Q 串口logger：

```bash
RUN_SERIAL_LOGGER=1 ./scripts/run_demo.sh
```

如果 8080 端口已经被占用：

```bash
DASHBOARD_PORT=18080 ./scripts/run_demo.sh
```

本次 bring-up 已确认：

```text
- Camera AI 通过 NCNN 读取 models/yolo_bear_ncnn_model。
- data/debug_frames/latest_camera_ai.jpg 可以生成。
- Dashboard / 返回 HTTP 200。
- Dashboard /camera/latest.jpg 返回 HTTP 200 image/jpeg。
- 停止demo后，不会留下 Camera AI 或 dashboard 进程。
```

---

## 演示模式（远程执行器控制）

仪表盘内置了 **演示模式** 面板，用于在发表时安全地进行远程执行器控制。
操作者可以通过 Raspberry Pi 向 Arduino 连接的舵机/机构手动发送命令。

### 架构

```text
Dashboard (浏览器)
  ↓ Tailscale / LAN
Raspberry Pi 4B (仪表盘后端)
  ↓ USB串口 (有线)
Arduino Uno Q
  ↓ GPIO / PCA9685
舵机 / 蜂蜜释放机构
```

- 无线/远程部分 **仅限** Dashboard → Raspberry Pi（通过 Tailscale 或 LAN）。
- Raspberry Pi → Arduino 之间保持 **有线USB串口** 以确保稳定性。
- 仪表盘绝不直接与 Arduino 通信。

### 快速开始

启动完整演示（Camera AI + 安全控制 + 仪表盘）:

```bash
./scripts/run_demo.sh
```

或仅启动仪表盘并开启演示模式以进行硬件测试:

```bash
python raspberry_pi/dashboard/app.py \
  --log-dir data/logs \
  --log-file data/logs/feeding_decision_log.csv \
  --camera-log-file data/logs/camera_ai_log.csv \
  --debug-frame-dir data/debug_frames \
  --demo-serial-port /dev/ttyACM0 \
  --demo-baudrate 115200 \
  --demo-command-log-file data/logs/demo_commands.csv \
  --host 0.0.0.0 \
  --port 8080
```

在同一 Tailscale 网络上的任意浏览器中打开 `http://<pi-ip>:8080`。

### 使用方法

1. 打开仪表盘。演示模式面板默认显示 **DISABLED**。
2. 点击 **Enable Demo Mode** 启用手动控制。
3. 使用控制按钮:
   - **Release / Open** — 向 Arduino 发送 `RELEASE`（需先启用演示模式）
   - **Stop / Close** — 向 Arduino 发送 `STOP`（始终可用）
   - **Test Motion** — 向 Arduino 发送 `TEST`（需先启用演示模式）
   - **Emergency Stop** — 立即发送 `STOP`，禁用演示模式并锁定控制
4. 状态表显示:
   - 最后发送的命令
   - 命令时间戳
   - 串口连接状态（`CONNECTED` / `SIMULATION_MODE` / `ERROR`）
   - 结果（`SENT` / `SIMULATED` / `BLOCKED` / `ERROR`）
   - 消息

### 安全行为

- 默认状态为 **STOP / 关闭**。
- 发送 `Release` 或 `Test` 命令前，必须手动启用演示模式。
- `Stop / Close` 和 `Emergency Stop` **始终** 可用。
- Emergency Stop 立即发送 `STOP` 并禁用演示模式。
- 串口错误时，系统自动回退到 **仿真模式**，不控制硬件。

### 仿真模式（无硬件排练）

如果 Arduino 未连接或串口不可用，仪表盘自动以仿真模式运行:

```bash
# 自动回退 — 不连接 Arduino 直接运行
python raspberry_pi/dashboard/app.py --host 0.0.0.0 --port 8080

# 或显式强制仿真模式
python raspberry_pi/dashboard/app.py --demo-force-simulation --host 0.0.0.0 --port 8080
```

在仿真模式下:
- UI 中所有按钮正常工作。
- 命令记录到 `data/logs/demo_commands.csv`。
- 不向硬件发送串口数据。
- 状态显示 `SIMULATION_MODE`。

### API 端点

仪表盘后端提供以下演示模式 REST 端点:

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/demo-mode` | POST | 启用/禁用演示模式 (`{"enabled": true/false}`) |
| `/api/demo-command` | POST | 发送通用命令 (`{"command": "RELEASE"}`) |
| `/api/demo/release` | POST | 发送 RELEASE 命令 |
| `/api/demo/stop` | POST | 发送 STOP 命令 |
| `/api/demo/test` | POST | 发送 TEST 命令 |
| `/api/demo/emergency-stop` | POST | 发送 EMERGENCY_STOP 命令 |
| `/api/demo-status` | GET | 获取当前演示状态 |

所有端点在使用 `Accept: application/json` 或 `Content-Type: application/json`
调用时返回 JSON。从浏览器 UI 操作时，使用 HTML form POST 并重定向回仪表盘。

### 串口命令

Raspberry Pi 通过 USB 串口向 Arduino 发送以下简单字符串命令:

| 命令 | 串口字符串 | 说明 |
|---|---|---|
| Release / Open | `RELEASE\n` | 启动蜂蜜释放机构 |
| Stop / Close | `STOP\n` | 停止机构（安全默认） |
| Test Motion | `TEST\n` | 执行短测试动作 |
| Emergency Stop | `STOP\n` | 与 STOP 相同，同时禁用演示模式 |

### 命令日志

所有演示命令记录到 CSV:

```text
data/logs/demo_commands.csv
```

CSV列: `timestamp`, `command`, `serial_command`, `demo_enabled`,
`serial_status`, `result`, `message`, `emergency_stop`

### CLI 选项

| 选项 | 默认值 | 说明 |
|---|---|---|
| `--demo-serial-port` | `/dev/ttyACM0` | Arduino 连接的串口 |
| `--demo-baudrate` | `115200` | 串口波特率 |
| `--demo-command-log-file` | `data/logs/demo_commands.csv` | 演示命令 CSV 日志路径 |
| `--demo-serial-timeout` | `1.0` | 串口写入超时（秒） |
| `--demo-serial-reset-delay` | `2.0` | 打开串口后等待时间（秒） |
| `--demo-force-simulation` | (off) | 即使串口存在也强制仿真模式 |

---

## 数据格式说明

- Arduino Uno Q 发送 **JSON Lines**。
- Camera AI 也发送 **JSON Lines**。
- Raspberry Pi 保存 **CSV日志**。
- 在加入实时时钟之前，`timestamp` 以 **uptime** (`T+<ms>`) 形式处理。
- 完整schema请参考 `docs/interface_spec.md` 和 `docs/camera_ai_interface_spec.md`。

---

## 一句话总结

本项目使用 Raspberry Pi 4B 和 BUFFALO BSW500M USB 摄像头进行基于 YOLO 的熊接近检测，同时保留 Arduino/接触垫的安全判断逻辑，只有在 AI 检测、接触确认、蜂蜜余量和安全条件全部满足时才允许释放蜂蜜。
