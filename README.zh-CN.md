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
- /dev/video0: 实际图像流设备
- /dev/video1: metadata device，不能用于图像采集
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

硬件和运行时前提：

```text
- 目标设备: Raspberry Pi 4B 4GB
- 摄像头: BUFFALO BSW500M USB Web摄像头
- 图像采集设备: /dev/video0
- metadata device: /dev/video1，不能用于采集
- 模型路径: models/yolo_bear.pt
- 推荐分辨率: 640x480 或 320x240
- 推荐FourCC: 先MJPG，失败时fallback到YUYV
- 失败行为: ai_bear_approaching=false
```

如果缺少 `models/yolo_bear.pt`，系统输出 `AI_MODEL_LOAD_ERROR`，设置 `ai_model_ok=false`，并保持故障安全状态。

Camera AI 运行命令：

```bash
python3 -m compileall -q raspberry_pi/camera_ai
python3 raspberry_pi/camera_ai/camera_test.py --device /dev/video0
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
| `models/` | 本地YOLO模型权重目录。期望路径是 `models/yolo_bear.pt`。默认不提交到Git。 |
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
[ ] 放置 models/yolo_bear.pt
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
- Raspberry Pi 4B 使用 BUFFALO BSW500M 的 /dev/video0 进行图像采集
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
[ ] Raspberry Pi 可以从 /dev/video0 采集图像
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

1. 将轻量YOLO模型放到 `models/yolo_bear.pt`。
2. 确认摄像头。
   ```bash
   python3 raspberry_pi/camera_ai/camera_test.py --device /dev/video0
   ```
3. 运行一次AI流程。
   ```bash
   python3 -m raspberry_pi.camera_ai.run_camera_ai --terminal-status --no-jsonl --once
   ```

### Raspberry Pi 仪表盘

1. 安装依赖。
   ```bash
   pip install -r raspberry_pi/dashboard/requirements.txt
   ```
2. 启动仪表盘。
   ```bash
   python raspberry_pi/dashboard/app.py --log-dir data/logs --host 0.0.0.0 --port 8080
   ```
3. 打开 `http://<pi-ip>:8080` 查看最新状态。

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
