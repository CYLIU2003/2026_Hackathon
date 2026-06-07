# A1 Front Paw Contact Pad System

## Overview

This repository contains the prototype for the **Front Paw Contact Pad System** in the A1 **Bear Honey Buffet** hackathon project.

The goal is to detect or simulate whether a bear has arrived and touched a front paw contact pad, then safely decide whether to send a honey release signal to the honeycomb mechanism.

The first version does **not** require real sensors.  
It uses simulated inputs so that the control logic can be developed before hardware parts are finalized.

---

## Project Vision

The whole A1 system is divided into two major parts.

```text
[Bear]
  ↓
[Front Paw Contact Pad System]  ← this repository / LIU side
  ↓ release signal
[Honeycomb / Bee Hive Mechanism] ← Goda-san side
  ↓
[Honey is released]
```

This repository focuses only on the electronic/control side.

---

## What This System Does

The Front Paw Contact Pad System checks:

```text
1. Has a bear arrived?
2. Is the front paw touching the pad?
3. Is there enough honey?
4. Is the system safe?
5. Should the honey release mechanism be activated?
```

If all conditions are satisfied, the system outputs:

```text
RELEASE_ON
```

Otherwise, it outputs:

```text
RELEASE_OFF
```

---

## Hardware Concept

### Arduino Uno Q

Arduino Uno Q is used as the main field controller.

Expected responsibilities:

```text
- contact pad input
- simulated sensor input
- threshold judgement
- release decision logic
- LED / GPIO / release signal output
- serial or network communication
```

Arduino Uno Q is suitable for this role because it combines a Linux-capable MPU side and a real-time MCU side. The official Arduino documentation describes it as a dual-architecture board combining a Qualcomm QRB2210 MPU running Debian-based Linux with an STM32U585 MCU for real-time control.

Reference:

```text
https://docs.arduino.cc/hardware/uno-q
https://docs.arduino.cc/tutorials/uno-q/user-manual/
```

### Raspberry Pi 4B

Raspberry Pi 4B is used as the upper-level logging and demo device.

Expected responsibilities:

```text
- receive data from Arduino Uno Q
- save CSV logs
- show dashboard
- visualize latest state
- support presentation demo
- remote access by SSH/Tailscale
```

The Raspberry Pi should not be the only safety controller.  
The default release decision should remain on Arduino Uno Q.

---

## System Architecture

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

The first MVP should demonstrate the following.

### Input

```text
simulated_bear_detected
simulated_paw_contact
simulated_honey_amount_percent
simulated_system_safe
emergency_stop
```

### Logic

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

### Output

```text
- RELEASE_ON / RELEASE_OFF
- LED ON/OFF
- JSON Lines over serial
- CSV log on Raspberry Pi
```

---

## State Machine

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

Error handling:

```text
ANY_STATE
  ↓ invalid data / emergency stop / communication error
ERROR_SAFE
  ↓ RESET command
IDLE
```

In `ERROR_SAFE`, release must always be OFF.

---

## Safety Policy

This project is a hackathon prototype.  
It must not harm animals or people.

Do not:

```text
- use high voltage/current on a contact pad
- design an electric shock system
- test on real bears without expert supervision
- claim real bear resistance values without valid measurement
- allow uncontrolled honey release
```

Always:

```text
- default to RELEASE_OFF
- use simulated inputs first
- keep release duration limited
- log every important state change
- separate contact pad logic from honeycomb mechanism
```

---

## Data Format

Arduino Uno Q should send JSON Lines.

Example:

```json
{"timestamp":"2026-05-23T18:30:00+09:00","bear_detected":false,"paw_contact":false,"honey_amount_percent":80,"system_safe":true,"emergency_stop":false,"release_state":"RELEASE_OFF","state":"IDLE","event":"IDLE"}
{"timestamp":"2026-05-23T18:30:05+09:00","bear_detected":true,"paw_contact":true,"honey_amount_percent":80,"system_safe":true,"emergency_stop":false,"release_state":"RELEASE_ON","state":"RELEASING","event":"RELEASE_START"}
```

Raspberry Pi should save CSV logs.

Example:

```csv
timestamp,bear_detected,paw_contact,honey_amount_percent,system_safe,emergency_stop,release_state,state,event
2026-05-23T18:30:00+09:00,false,false,80,true,false,RELEASE_OFF,IDLE,IDLE
2026-05-23T18:30:05+09:00,true,true,80,true,false,RELEASE_ON,RELEASING,RELEASE_START
```

---

## Recommended Repository Layout

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

---

## Development Roadmap

### Phase 1: Design

```text
[ ] Create block diagram
[ ] Create state transition diagram
[ ] Define JSON/CSV interface
[ ] Define release signal interface with honeycomb mechanism side
```

### Phase 2: Uno Q Standalone Prototype

```text
[ ] Simulated bear_detected input
[ ] Simulated paw_contact input
[ ] Simulated honey_amount input
[ ] Release decision logic
[ ] LED or serial RELEASE_ON/OFF output
```

### Phase 3: Raspberry Pi Logger

```text
[ ] Receive JSON Lines from Uno Q
[ ] Validate message format
[ ] Save CSV log
[ ] Print latest state in terminal
```

### Phase 4: Demo Dashboard

```text
[ ] Show latest bear_detected
[ ] Show latest paw_contact
[ ] Show honey_amount
[ ] Show release_state
[ ] Show recent event log
```

### Phase 5: Hardware Replacement

```text
[ ] Replace simulated bear_detected with real sensor candidate
[ ] Replace simulated paw_contact with real sensor candidate
[ ] Replace simulated honey_amount with real sensor candidate
[ ] Test with dummy objects only
```

---

## How to Explain This to the Team

Use the following explanation.

```text
I will develop the front paw contact pad system as a separate electronic/control module.
Arduino Uno Q will be used as the main controller for simulated sensor inputs and release decision logic.
Raspberry Pi 4B will be used for logging, dashboard, and presentation demo.
Since I do not have real sensors now, I will first build the logic using simulated inputs.
Later, the simulated inputs can be replaced with actual sensors.
```

---

## Current Assumptions

```text
- The honeycomb mechanism can receive a simple RELEASE_ON/OFF signal.
- Physical sensors are not available at the beginning.
- The first demo can use LED/serial output instead of a pump or valve.
- No real animal test will be conducted.
- The project is for hackathon demonstration and concept validation.
```

---

## Definition of Done for MVP v0.1

```text
[ ] Uno Q can generate simulated inputs
[ ] Uno Q can decide RELEASE_ON/OFF
[ ] RELEASE_ON/OFF is visible through LED or serial output
[ ] Raspberry Pi can receive the state
[ ] Raspberry Pi can save CSV logs
[ ] Safety fallback to RELEASE_OFF is implemented
[ ] README explains how the system works
[ ] Team can understand the boundary between contact pad and honeycomb mechanism
```

---

## Getting Started (MVP Simulation)

This prototype uses **simulated sensor inputs** and does not require real sensors.

### Arduino Uno Q

1. Open `arduino_uno_q/contact_pad_controller/contact_pad_controller.ino`.
2. Build and upload to Arduino Uno Q.
3. Open the serial monitor at **115200 baud**.
4. You should see JSON Lines output.

### Raspberry Pi Logger

1. Install dependencies:
   ```bash
   pip install -r raspberry_pi/logger/requirements.txt
   ```
2. Run the logger:
   ```bash
   python raspberry_pi/logger/serial_logger.py --serial-port /dev/ttyACM0 --baudrate 115200
   ```
3. CSV logs are saved to `data/logs/`.

### Raspberry Pi Dashboard

1. Install dependencies:
   ```bash
   pip install -r raspberry_pi/dashboard/requirements.txt
   ```
2. Run the dashboard:
   ```bash
   python raspberry_pi/dashboard/app.py --log-dir data/logs --host 0.0.0.0 --port 8080
   ```
3. Open `http://<pi-ip>:8080` to view the latest state.

---

## Data Format Notes

- Arduino Uno Q sends **JSON Lines**.
- Raspberry Pi saves **CSV logs**.
- `timestamp` is emitted as **uptime** (`T+<ms>`) until a real-time clock is added.
- See `docs/interface_spec.md` for the full schema.

---

## One-Sentence Summary

This project uses Arduino Uno Q as the main front paw contact pad controller and Raspberry Pi 4B as the logging/dashboard device, first using simulated inputs to safely validate the honey release decision logic before integrating real sensors.
