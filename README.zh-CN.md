# A1 前掌接触垫系统 / Front Paw Contact Pad System

## 概要

本仓库用于 A1 **Bear Honey Buffet** 黑客松项目中的 **Front Paw Contact Pad System** 原型开发。

本系统的目标是：检测或模拟熊是否接近并用前掌触碰接触垫，然后根据检测结果，向蜂巢机构发送安全的蜂蜜释放信号。

初始版本不需要真实传感器。  
在传感器尚未准备好的阶段，本系统先使用模拟输入来验证控制逻辑。

---

## 项目愿景

A1系统整体可以分为两个主要部分。

```text
[Bear]
  ↓
[Front Paw Contact Pad System]  ← 本仓库 / LIU负责
  ↓ release signal
[Honeycomb / Bee Hive Mechanism] ← Goda负责
  ↓
[Honey is released]
```

本仓库只负责电子控制、检测逻辑、数据记录和演示部分。

---

## 本系统要做什么

Front Paw Contact Pad System 会判断以下内容。

```text
1. 熊是否到来
2. 前掌是否接触接触垫
3. 蜂蜜剩余量是否足够
4. 系统是否处于安全状态
5. 是否可以启动蜂蜜释放机构
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

Arduino Uno Q 用作现场侧的主控制板。

主要职责：

```text
- 接触垫输入
- 模拟传感器输入
- 阈值判断
- 蜂蜜释放判定逻辑
- LED / GPIO / release signal 输出
- serial 或 network 通信
```

Arduino Uno Q 同时具有可运行Linux的MPU侧和实时控制用MCU侧，因此适合承担现场控制任务。

参考：

```text
https://docs.arduino.cc/hardware/uno-q
https://docs.arduino.cc/tutorials/uno-q/user-manual/
```

### Raspberry Pi 4B

Raspberry Pi 4B 用作上位侧的日志记录、可视化和演示设备。

主要职责：

```text
- 接收 Arduino Uno Q 的状态数据
- 保存CSV日志
- 显示仪表盘
- 可视化最新状态
- 支持演示和发表
- 通过 SSH / Tailscale 进行远程访问
```

Raspberry Pi 不应作为唯一的安全控制器。  
基本的释放判断应放在 Arduino Uno Q 侧。

---

## 系统架构

```text
┌────────────────────────────┐
│ Bear / Simulated Bear       │
└─────────────┬──────────────┘
              ↓
┌────────────────────────────┐
│ Front Paw Contact Pad       │
│ - contact input             │
│ - future pressure/R sensor  │
│ - currently simulated input │
└─────────────┬──────────────┘
              ↓
┌────────────────────────────┐
│ Arduino Uno Q               │
│ - sensor simulation         │
│ - decision logic            │
│ - RELEASE_ON/OFF output     │
│ - serial JSON output        │
└─────────────┬──────────────┘
              ↓
┌────────────────────────────┐
│ Raspberry Pi 4B             │
│ - receive state             │
│ - CSV logging               │
│ - dashboard                 │
│ - visualization             │
└─────────────┬──────────────┘
              ↓
┌────────────────────────────┐
│ Presentation / Team Demo    │
└────────────────────────────┘
```

---

## MVP v0.1

第一个MVP需要实现以下内容。

### 输入

```text
simulated_bear_detected
simulated_paw_contact
simulated_honey_amount_percent
simulated_system_safe
emergency_stop
```

### 控制逻辑

```text
if bear_detected
and paw_contact
and honey_amount_percent >= threshold
and system_safe
and not emergency_stop:
    release_state = RELEASE_ON
else:
    release_state = RELEASE_OFF
```

### 输出

```text
- RELEASE_ON / RELEASE_OFF
- LED ON/OFF
- JSON Lines over serial
- CSV log on Raspberry Pi
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
- RELEASE_ON 必须有时间限制
- 重要状态变化必须记录日志
- 接触垫控制系统与蜂巢机械结构必须分离
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
│  └─ interface_spec.md
├─ arduino_uno_q/
│  ├─ contact_pad_controller/
│  │  ├─ contact_pad_controller.ino
│  │  └─ config.h
│  └─ README.md
├─ raspberry_pi/
│  ├─ logger/
│  │  ├─ serial_logger.py
│  │  └─ requirements.txt
│  ├─ dashboard/
│  │  ├─ app.py
│  │  └─ requirements.txt
│  └─ README.md
├─ data/
│  └─ logs/
├─ examples/
│  └─ sample_log.csv
└─ scripts/
   └─ run_demo.sh
```

---

## 开发路线图

### Phase 1: 设计

```text
[ ] 创建系统框图
[ ] 创建状态机图
[ ] 定义 JSON/CSV 接口
[ ] 定义给蜂巢机构侧的 release signal
```

### Phase 2: Uno Q 单体原型

```text
[ ] simulated bear_detected input
[ ] simulated paw_contact input
[ ] simulated honey_amount input
[ ] release decision logic
[ ] 通过LED或serial输出 RELEASE_ON/OFF
```

### Phase 3: Raspberry Pi 日志程序

```text
[ ] 从 Uno Q 接收 JSON Lines
[ ] 验证消息格式
[ ] 保存为CSV日志
[ ] 在终端显示最新状态
```

### Phase 4: 演示仪表盘

```text
[ ] 显示最新 bear_detected
[ ] 显示最新 paw_contact
[ ] 显示 honey_amount
[ ] 显示 release_state
[ ] 显示最近事件日志
```

### Phase 5: 替换为真实传感器

```text
[ ] 用真实传感器候选替换 simulated bear_detected
[ ] 用真实传感器候选替换 simulated paw_contact
[ ] 用真实传感器候选替换 simulated honey_amount
[ ] 仅使用假物体或安全测试物进行测试
```

---

## 向团队说明

```text
I will develop the front paw contact pad system as a separate electronic/control module.
Arduino Uno Q will be used as the main controller for simulated sensor inputs and release decision logic.
Raspberry Pi 4B will be used for logging, dashboard, and presentation demo.
Since I do not have real sensors now, I will first build the logic using simulated inputs.
Later, the simulated inputs can be replaced with actual sensors.
```

---

## 当前假设

```text
- 蜂巢机构侧可以接收简单的 RELEASE_ON/OFF 信号
- 初始阶段不使用物理传感器
- 第一次演示可以用LED或serial输出代替泵和阀门
- 不进行真实动物测试
- 本项目是黑客松用概念验证
```

---

## MVP v0.1 完成条件

```text
[ ] Uno Q 可以生成模拟输入
[ ] Uno Q 可以判断 RELEASE_ON/OFF
[ ] 通过LED或serial可以看到 RELEASE_ON/OFF
[ ] Raspberry Pi 可以接收状态数据
[ ] Raspberry Pi 可以保存CSV日志
[ ] 异常时可以回到 RELEASE_OFF
[ ] README解释了系统工作方式
[ ] 团队可以理解接触垫系统与蜂巢机构之间的边界
```

---

## 一句话总结

本项目使用 Arduino Uno Q 作为前掌接触垫的主控制器，使用 Raspberry Pi 4B 作为日志记录和仪表盘设备。初期通过模拟输入安全地验证蜂蜜释放判断逻辑，之后再替换为真实传感器。
