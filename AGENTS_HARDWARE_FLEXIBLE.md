# AGENTS_HARDWARE_FLEXIBLE.md

## AI Agent Instructions: Hardware-Flexible Front Paw Contact Pad System

### Project

A1 Bear Honey Buffet  
Module: Front Paw Contact Pad System  
Owner: LIU Chengyang / 刘承洋_C.Y.LIU

This document instructs AI agents, Codex, GitHub Copilot, and human developers to implement the system so that it can work with multiple hardware patterns.

Supported patterns:

```text
Pattern A: Arduino Uno Q only
Pattern B: Arduino Uno Q + Raspberry Pi 4B
Pattern C: ESP32 only
Pattern D: Raspberry Pi 4B + ESP32
```

---

## 1. Core Architecture

Do not design the system around one specific board name.

Use this abstract architecture:

```text
[Sensor / Simulated Input]
          ↓
[Edge Controller]
          ↓
[Release Signal Output]
          ↓
[Optional Host Device]
          ↓
[Logging / Dashboard / Demo]
```

### Edge Controller

The Edge Controller is the field-side controller.

Possible devices:

```text
- Arduino Uno Q
- ESP32
```

Responsibilities:

```text
- read or simulate sensor inputs
- run the state machine
- perform safety judgement
- decide RELEASE_ON / RELEASE_OFF
- control LED / GPIO / future actuator signal
- output JSON Lines status
```

### Optional Host Device

The Optional Host Device is the upper-level logging and visualization device.

Possible devices:

```text
- Raspberry Pi 4B
- PC
- none
```

Responsibilities:

```text
- receive JSON Lines from Edge Controller
- save CSV logs
- show dashboard
- visualize latest state
- support presentation demo
```

---

## 2. Most Important Rule

The release decision logic must run on the Edge Controller.

Do not move the main safety decision only to Raspberry Pi.

Even if Raspberry Pi stops, the Edge Controller must still guarantee:

```text
- default RELEASE_OFF
- emergency_stop handling
- timeout handling
- cooldown handling
- invalid input handling
```

---

## 3. Hardware Patterns

## Pattern A: Arduino Uno Q only

```text
[Simulated Input / Future Sensors]
          ↓
[Arduino Uno Q]
  - state machine
  - release decision
  - LED / release signal
  - JSON Lines serial output
```

Rules:

```text
- Arduino Uno Q is the Edge Controller.
- Raspberry Pi must not be required.
- Serial Monitor output must be enough for MVP demo.
```

---

## Pattern B: Arduino Uno Q + Raspberry Pi 4B

```text
[Simulated Input / Future Sensors]
          ↓
[Arduino Uno Q]
  - state machine
  - release decision
  - JSON Lines output
          ↓ USB serial / network
[Raspberry Pi 4B]
  - CSV logging
  - dashboard
  - visualization
```

Rules:

```text
- Arduino Uno Q is the Edge Controller.
- Raspberry Pi is only the Optional Host Device.
- Safety decision stays on Arduino Uno Q.
```

---

## Pattern C: ESP32 only

```text
[Simulated Input / Future Sensors]
          ↓
[ESP32]
  - state machine
  - release decision
  - LED / release signal
  - serial logs
  - optional Wi-Fi dashboard
```

Rules:

```text
- ESP32 is the Edge Controller.
- Raspberry Pi must not be required.
- Serial output is mandatory.
- Wi-Fi dashboard is optional.
- System must work even when Wi-Fi is disabled.
```

---

## Pattern D: Raspberry Pi 4B + ESP32

```text
[Simulated Input / Future Sensors]
          ↓
[ESP32]
  - state machine
  - release decision
  - JSON Lines output
          ↓ USB serial / UART / Wi-Fi
[Raspberry Pi 4B]
  - CSV logging
  - dashboard
  - visualization
```

Rules:

```text
- ESP32 is the Edge Controller.
- Raspberry Pi is the Optional Host Device.
- Safety decision stays on ESP32.
- Raspberry Pi should handle logging and visualization only.
```

---

## 4. Common MVP Requirements

The MVP must work even without physical sensors.

### Inputs

```text
simulated_bear_detected
simulated_paw_contact
simulated_honey_amount_percent
simulated_system_safe
emergency_stop
```

### Converted control variables

```text
bear_detected
paw_contact
honey_amount_percent
system_safe
emergency_stop
```

### Release condition

`RELEASE_ON` is allowed only when all conditions are true:

```text
bear_detected == true
paw_contact == true
honey_amount_percent >= honey_min_threshold_percent
system_safe == true
emergency_stop == false
```

Otherwise:

```text
release_state = RELEASE_OFF
```

### Outputs

```text
release_state
state
event
LED or GPIO output
JSON Lines status message
```

---

## 5. Common State Machine

All hardware targets must use the same state machine.

```text
IDLE
  ↓ bear_detected
BEAR_DETECTED
  ↓ paw_contact confirmed
CONTACT_CONFIRMED
  ↓ honey enough and system safe
READY_TO_RELEASE
  ↓ release starts
RELEASING
  ↓ max_release_duration_ms elapsed
COOLDOWN
  ↓ cooldown_after_release_ms elapsed
IDLE
```

Error path:

```text
ANY_STATE
  ↓ emergency_stop / invalid input / internal error
ERROR_SAFE
  ↓ reset
IDLE
```

In `ERROR_SAFE`, output must always be:

```text
RELEASE_OFF
```

---

## 6. Safety Rules

AI agents must obey these rules.

```text
- Default state must be RELEASE_OFF.
- On error, output RELEASE_OFF.
- On communication loss, Edge Controller stays safe.
- On invalid sensor value, output RELEASE_OFF.
- RELEASE_ON must have timeout.
- COOLDOWN must be implemented after release.
- No high-voltage contact measurement.
- No electric shock design.
- No real bear testing assumption.
- Do not claim real bear resistance data without valid measurement.
```

---

## 7. Communication Standard

When a Host Device is used, the Edge Controller sends data as JSON Lines.

Preferred transport:

```text
1. serial_usb
2. uart
3. wifi_http
4. wifi_websocket
5. wifi_mqtt
```

MVP priority:

```text
serial_usb
```

### JSON Lines example

```json
{"timestamp":"2026-05-29T12:00:00+09:00","hardware_target":"esp32_plus_raspberry_pi","edge_controller":"esp32","host_device":"raspberry_pi_4b","state":"RELEASING","event":"RELEASE_START","bear_detected":true,"paw_contact":true,"honey_amount_percent":80,"system_safe":true,"emergency_stop":false,"release_state":"RELEASE_ON","error_code":"ERR_NONE"}
```

Standalone mode must also print JSON Lines to Serial Monitor.

---

## 8. Hardware Target Configuration

Use a hardware target configuration instead of hardcoding board assumptions.

### ESP32 only

```json
{
  "hardware_target": "esp32",
  "edge_controller": "esp32",
  "host_device": null,
  "communication_backend": "serial_usb",
  "use_simulated_inputs": true,
  "enable_dashboard": false,
  "enable_wifi_dashboard": false
}
```

### ESP32 + Raspberry Pi

```json
{
  "hardware_target": "esp32_plus_raspberry_pi",
  "edge_controller": "esp32",
  "host_device": "raspberry_pi_4b",
  "communication_backend": "serial_usb",
  "use_simulated_inputs": true,
  "enable_dashboard": true
}
```

### Arduino Uno Q only

```json
{
  "hardware_target": "uno_q",
  "edge_controller": "arduino_uno_q",
  "host_device": null,
  "communication_backend": "serial_usb",
  "use_simulated_inputs": true,
  "enable_dashboard": false
}
```

### Arduino Uno Q + Raspberry Pi

```json
{
  "hardware_target": "uno_q_plus_raspberry_pi",
  "edge_controller": "arduino_uno_q",
  "host_device": "raspberry_pi_4b",
  "communication_backend": "serial_usb",
  "use_simulated_inputs": true,
  "enable_dashboard": true
}
```

---

## 9. Board-Specific Rules

Common logic must not be duplicated differently for each board.

Keep the following common:

```text
- release condition
- state machine
- JSON Lines schema
- CSV schema
- safety rules
- event names
- error codes
```

Board-specific parts may differ:

```text
- pin mapping
- serial port name
- Wi-Fi availability
- board initialization
- analog input range
```

---

## 10. Pin Mapping Rules

Do not scatter pin numbers in the code.

Put board-specific pin mappings in config files.

### ESP32 example

```cpp
const int PIN_RELEASE_LED = 2;
const int PIN_RELEASE_SIGNAL = 25;
const int PIN_EMERGENCY_STOP = 26;
const int PIN_SIM_BEAR_INPUT = 32;
const int PIN_SIM_CONTACT_INPUT = 33;
const int PIN_CONTACT_ANALOG = 34;
const int PIN_HONEY_ANALOG = 35;
```

### Arduino Uno Q example

```cpp
const int PIN_RELEASE_LED = 13;
const int PIN_RELEASE_SIGNAL = 8;
const int PIN_EMERGENCY_STOP = 7;
const int PIN_SIM_BEAR_INPUT = 2;
const int PIN_SIM_CONTACT_INPUT = 3;
const int PIN_CONTACT_ANALOG = A0;
const int PIN_HONEY_ANALOG = A1;
```

---

## 11. Raspberry Pi Logger Rules

Raspberry Pi logger must work with both ESP32 and Arduino Uno Q.

It should not depend strongly on board-specific behavior.

Required accepted fields:

```text
timestamp
hardware_target
edge_controller
host_device
state
event
bear_detected
paw_contact
honey_amount_percent
system_safe
emergency_stop
release_state
error_code
```

Serial port must be configurable.

Examples:

```text
/dev/ttyACM0
/dev/ttyUSB0
COM3
COM4
```

---

## 12. Optional ESP32 Wi-Fi Features

ESP32 may optionally provide a small Wi-Fi dashboard.

Optional endpoints:

```text
GET /status
POST /simulate
POST /reset
```

Example `/status` response:

```json
{
  "hardware_target": "esp32",
  "state": "IDLE",
  "bear_detected": false,
  "paw_contact": false,
  "honey_amount_percent": 80,
  "release_state": "RELEASE_OFF"
}
```

These features are optional.  
The MVP must not depend on Wi-Fi.

---

## 13. Recommended Repository Structure

```text
a1-front-paw-contact-pad/
├─ AGENTS_HARDWARE_FLEXIBLE.md
├─ HARDWARE_TARGETS.md
├─ VARIABLES.md
├─ README.md
├─ docs/
│  ├─ architecture.md
│  ├─ state_machine.md
│  ├─ interface_spec.md
│  └─ hardware_selection.md
├─ edge_controller/
│  ├─ common/
│  │  ├─ message_schema.md
│  │  └─ decision_logic.md
│  ├─ esp32/
│  │  └─ contact_pad_controller/
│  │     ├─ contact_pad_controller.ino
│  │     └─ config.h
│  └─ uno_q/
│     └─ contact_pad_controller/
│        ├─ contact_pad_controller.ino
│        └─ config.h
├─ host_device/
│  └─ raspberry_pi/
│     ├─ logger/
│     │  ├─ serial_logger.py
│     │  └─ requirements.txt
│     └─ dashboard/
│        ├─ app.py
│        └─ requirements.txt
├─ examples/
│  ├─ sample_esp32_output.jsonl
│  ├─ sample_uno_q_output.jsonl
│  └─ sample_log.csv
└─ data/
   └─ logs/
```

---

## 14. Implementation Order

### Step 1: Create common docs

```text
docs/architecture.md
docs/state_machine.md
docs/interface_spec.md
docs/hardware_selection.md
```

### Step 2: Implement ESP32 standalone MVP

Reason: ESP32-only is likely the simplest fallback.

```text
edge_controller/esp32/contact_pad_controller/
```

Features:

```text
- simulated inputs
- state machine
- release decision
- LED output
- JSON Lines serial output
```

### Step 3: Implement Raspberry Pi logger

The logger must accept both ESP32 and Uno Q JSON Lines.

```text
host_device/raspberry_pi/logger/
```

### Step 4: Implement Uno Q version

Use the same state machine and JSON schema.

```text
edge_controller/uno_q/contact_pad_controller/
```

### Step 5: Implement optional dashboard

```text
host_device/raspberry_pi/dashboard/
```

---

## 15. Test Matrix

All hardware targets must pass these tests.

| Case | bear_detected | paw_contact | honey_amount_percent | system_safe | emergency_stop | Expected |
|---|---:|---:|---:|---:|---:|---|
| no_bear | false | false | 80 | true | false | RELEASE_OFF |
| bear_no_contact | true | false | 80 | true | false | RELEASE_OFF |
| contact_honey_low | true | true | 10 | true | false | RELEASE_OFF |
| ready_to_release | true | true | 80 | true | false | RELEASE_ON |
| unsafe_system | true | true | 80 | false | false | RELEASE_OFF |
| emergency_stop | true | true | 80 | true | true | RELEASE_OFF |
| timeout | true | true | 80 | true | false | RELEASE_OFF after timeout |
| cooldown | true | true | 80 | true | false | RELEASE_OFF during cooldown |

---

## 16. Do Not Do

AI agents must not:

```text
- assume Arduino Uno Q is always available
- assume ESP32 is always available
- make Raspberry Pi mandatory
- put release decision only on Raspberry Pi
- change release condition depending on hardware
- change JSON schema depending on hardware
- remove RELEASE_OFF fail-safe
- propose high-voltage contact measurement
- propose electric shock
- assume real bear experiments
- modify the honeycomb mechanism design without request
```

---

## 17. Team Explanation Template

```text
I updated the system design so it can support multiple hardware patterns.

The core architecture is:
- Edge Controller: sensing, decision logic, safety control, and release signal
- Optional Host Device: logging, dashboard, and demo visualization

This allows us to use:
1. Arduino Uno Q only
2. Arduino Uno Q + Raspberry Pi
3. ESP32 only
4. ESP32 + Raspberry Pi

The release decision logic always stays on the Edge Controller for safety.
Raspberry Pi is optional and mainly used for logging and visualization.
```

---

## 18. One-Sentence Summary

Design the system around `Edge Controller` and `Optional Host Device`, not around a fixed board name. ESP32-only, Raspberry Pi + ESP32, Arduino Uno Q-only, and Arduino Uno Q + Raspberry Pi must all use the same state machine, safety logic, and JSON interface.