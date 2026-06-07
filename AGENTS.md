# 指示書 / AGENTS.md

## Project

A1: Bear Honey Buffet  
Module: Front Paw Contact Pad System  
Target hardware: Arduino Uno Q + Raspberry Pi 4B  
Primary owner: LIU Chengyang / 刘承洋_C.Y.LIU

---

## 0. Mission

You are helping develop the Front Paw Contact Pad System for the A1 Bear Honey Buffet hackathon project.

The system detects/simulates whether a bear has arrived and touched the front paw contact pad, checks safety and honey availability conditions, and sends a safe release signal to the honeycomb mechanism.

The first prototype must work without real sensors by using simulated inputs.

---

## 1. System Boundary

### In scope

Implement and document:

```text
- simulated bear arrival input
- simulated front paw contact input
- simulated honey amount input
- release decision logic
- RELEASE_ON / RELEASE_OFF output
- serial communication
- CSV logging
- simple dashboard or terminal visualization
- block diagram
- state transition diagram
```

### Out of scope

Do not implement:

```text
- real animal experiments
- high-voltage / high-current contact measurement
- actual honeycomb mechanical structure
- queen excluder mechanism
- uncontrolled pump/valve operation
- AI model as a required component for MVP
```

---

## 2. Hardware Role Assignment

### Arduino Uno Q

Arduino Uno Q is the main field controller.

Use it for:

```text
- simulated sensor inputs
- future sensor inputs
- contact pad decision
- threshold judgement
- release signal output
- LED output
- low-latency I/O
```

Expected internal role split:

```text
MCU side:
  - deterministic control
  - GPIO
  - sensor/actuator I/O
  - safety fallback

Linux/MPU side:
  - local app logic
  - optional logging
  - optional AI/camera support
  - communication to Raspberry Pi
```

### Raspberry Pi 4B

Raspberry Pi 4B is the upper-level logging and demo device.

Use it for:

```text
- receiving data from Arduino Uno Q
- CSV logging
- dashboard
- visualization
- SSH/Tailscale remote access
- presentation support
```

Do not move the main release safety decision to Raspberry Pi unless explicitly requested.

---

## 3. Safety Rules

Always obey:

```text
- Default state must be RELEASE_OFF.
- On missing data, communication error, invalid value, or exception, output RELEASE_OFF.
- No high-voltage or high-current contact system.
- No direct animal testing.
- No electric shock concept.
- Use simulated inputs first.
- Add timeout to RELEASE_ON.
- Add cooldown after release.
```

Release is allowed only when:

```text
bear_detected == true
paw_contact == true
honey_amount_percent >= honey_min_threshold_percent
system_safe == true
emergency_stop == false
```

---

## 4. Initial MVP

Build MVP v0.1.

### Input

```text
simulated_bear_detected: bool
simulated_paw_contact: bool
simulated_honey_amount_percent: int 0-100
simulated_system_safe: bool
emergency_stop: bool
```

### Output

```text
release_state: RELEASE_ON | RELEASE_OFF
event: string
serial message: JSON Lines
optional LED: ON/OFF
```

### Example JSON Lines

```json
{"timestamp":"2026-05-23T18:30:00+09:00","bear_detected":false,"paw_contact":false,"honey_amount_percent":80,"system_safe":true,"release_state":"RELEASE_OFF","event":"IDLE"}
{"timestamp":"2026-05-23T18:30:05+09:00","bear_detected":true,"paw_contact":true,"honey_amount_percent":80,"system_safe":true,"release_state":"RELEASE_ON","event":"RELEASE_START"}
```

---

## 5. State Machine

Implement the logic as a state machine.

```text
IDLE
  ↓ bear_detected
BEAR_DETECTED
  ↓ paw_contact confirmed
CONTACT_CONFIRMED
  ↓ honey enough and system safe
READY_TO_RELEASE
  ↓ release command
RELEASING
  ↓ timeout
COOLDOWN
  ↓ cooldown done
IDLE
```

Error path:

```text
ANY_STATE
  ↓ invalid data / emergency stop / communication error
ERROR_SAFE
  ↓ RESET command
IDLE
```

In ERROR_SAFE, release must be OFF.

---

## 6. Recommended Repository Structure

```text
a1-front-paw-contact-pad/
├─ README.md
├─ AGENTS.md
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

Keep generated logs out of Git unless they are small sample logs.

---

## 7. Interface Contract

### Uno Q → Raspberry Pi

Preferred format: JSON Lines over USB serial or network socket.

Fields:

```json
{
  "timestamp": "ISO-8601 string",
  "bear_detected": "boolean",
  "paw_contact": "boolean",
  "raw_contact_value": "number or null",
  "honey_amount_percent": "integer 0-100",
  "system_safe": "boolean",
  "emergency_stop": "boolean",
  "release_state": "RELEASE_ON or RELEASE_OFF",
  "state": "IDLE / BEAR_DETECTED / CONTACT_CONFIRMED / READY_TO_RELEASE / RELEASING / COOLDOWN / ERROR_SAFE",
  "event": "string"
}
```

### Contact Pad → Honeycomb Mechanism

MVP signal:

```text
RELEASE_ON
RELEASE_OFF
```

Do not assume analog release control unless the team decides it.

Future optional fields:

```text
release_duration_ms
release_level_percent
```

---

## 8. Config Contract

Use a config file or constants.

```json
{
  "honey_min_threshold_percent": 20,
  "contact_confirm_duration_ms": 500,
  "max_release_duration_ms": 3000,
  "cooldown_after_release_ms": 5000,
  "serial_baudrate": 115200,
  "default_release_state": "RELEASE_OFF"
}
```

Do not hardcode thresholds across multiple files.

---

## 9. Coding Style

### Naming

Use explicit names.

Good:

```text
bear_detected
paw_contact
honey_amount_percent
release_state
emergency_stop
```

Bad:

```text
flag
x
data
val
mode
```

### Separation

Separate:

```text
- input simulation
- decision logic
- output control
- communication
- logging
- dashboard
```

Do not mix all logic in one long loop unless it is a very small MVP sketch.

---

## 10. Implementation Order

Follow this order.

### Step 1

Implement Uno Q standalone simulation.

```text
simulated input → decision logic → serial output / LED
```

### Step 2

Implement JSON Lines output.

### Step 3

Implement Raspberry Pi serial logger.

```text
serial input → CSV file
```

### Step 4

Implement simple dashboard.

```text
CSV/latest JSON → web page or terminal display
```

### Step 5

Prepare diagrams and demo script.

---

## 11. Test Cases

At minimum, test the following.

| Case | bear_detected | paw_contact | honey_amount | system_safe | expected |
|---|---:|---:|---:|---:|---|
| No bear | false | false | 80 | true | RELEASE_OFF |
| Bear but no contact | true | false | 80 | true | RELEASE_OFF |
| Contact but honey low | true | true | 10 | true | RELEASE_OFF |
| Contact and honey enough | true | true | 80 | true | RELEASE_ON |
| Unsafe system | true | true | 80 | false | RELEASE_OFF |
| Emergency stop | true | true | 80 | true + emergency | RELEASE_OFF |
| Timeout | true | true | 80 | true | RELEASE_OFF after max duration |

---

## 12. Documentation Requirements

Every implementation PR or update should include:

```text
- What was changed
- How to run
- What hardware is required
- Whether real sensors are required
- Expected output
- Known limitations
```

For MVP, explicitly say:

```text
This prototype uses simulated sensor inputs.
```

---

## 13. Communication Template for Team

When reporting progress to the team, use:

```text
I separated the front paw contact pad system into:
1. simulated sensor input,
2. release decision logic,
3. release signal output,
4. Raspberry Pi logging/dashboard.

Current version uses simulated inputs because I do not have real sensors yet.
The interface can later be replaced with real sensors.
```

---

## 14. Do Not Do

Do not:

```text
- implement harmful animal contact measurement
- assume we can test on real bears
- claim real resistance data without measurement
- make the Raspberry Pi the only safety controller
- remove fail-safe RELEASE_OFF behavior
- change the interface without documenting it
- mix honeycomb mechanism details into contact pad controller
```

---

## 15. Final Goal

The final goal is a demonstrable prototype:

```text
Arduino Uno Q:
  simulated bear/contact/honey inputs
  ↓
  safe release decision
  ↓
  RELEASE_ON/OFF output

Raspberry Pi 4B:
  receive state
  ↓
  log CSV
  ↓
  show dashboard
```

This proves the control architecture before real sensors and the physical honeycomb mechanism are integrated.
