# HARDWARE_TARGETS.md

## Hardware Target Definitions

This document defines supported hardware patterns for the A1 Front Paw Contact Pad System.

---

## 1. Common Concepts

### Edge Controller

The Edge Controller is the field-side controller.

Responsibilities:

```text
- sensor or simulated input
- state machine
- safety decision
- RELEASE_ON / RELEASE_OFF output
- GPIO / LED output
- JSON Lines status output
```

Candidates:

```text
- Arduino Uno Q
- ESP32
```

### Optional Host Device

The Optional Host Device is used for logging and visualization.

Responsibilities:

```text
- CSV logging
- dashboard
- visualization
- demo screen
- remote access
```

Candidates:

```text
- Raspberry Pi 4B
- PC
- none
```

### Optional Sensor Submodule

An optional sensor submodule can provide contact evidence to the Edge
Controller, but it does not own the release decision.

Current candidate:

```text
- ESP32 BIA measurement sketch
```

Rules:

```text
- Arduino Uno Q remains the authoritative safety controller.
- ESP32 BIA output is treated as an input signal only.
- If BIA data is stale or malformed while BIA mode is enabled, the controller
  must hold RELEASE_OFF and enter ERROR_SAFE.
```

---

## 2. Target: `uno_q`

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

Use this when Arduino Uno Q is used alone.

---

## 3. Target: `uno_q_plus_raspberry_pi`

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

Use this when Arduino Uno Q controls the pad and Raspberry Pi logs/displays data.

---

## 4. Target: `esp32`

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

Use this when ESP32 is used alone.

---

## 5. Target: `esp32_plus_raspberry_pi`

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

Use this when ESP32 controls the pad and Raspberry Pi logs/displays data.

---

## 5.1 Target: `uno_q_plus_esp32_bia_plus_raspberry_pi`

```json
{
  "hardware_target": "uno_q_plus_esp32_bia_plus_raspberry_pi",
  "edge_controller": "arduino_uno_q",
  "sensor_submodule": "esp32_bia",
  "host_device": "raspberry_pi_4b",
  "communication_backend": "serial_usb",
  "sensor_backend": "uart_jsonl",
  "use_simulated_inputs": false,
  "enable_bia_input": true,
  "enable_dashboard": true
}
```

Use this when Arduino Uno Q controls the release state machine, ESP32 provides
BIA contact evidence over UART, and Raspberry Pi logs/displays Arduino output.

---

## 6. Comparison

| Target | Edge Controller | Host Device | Logging | Dashboard | Complexity |
|---|---|---|---|---|---:|
| `uno_q` | Arduino Uno Q | none | serial only | no | low |
| `uno_q_plus_raspberry_pi` | Arduino Uno Q | Raspberry Pi 4B | CSV | yes | medium |
| `uno_q_plus_esp32_bia_plus_raspberry_pi` | Arduino Uno Q + ESP32 BIA input | Raspberry Pi 4B | CSV | yes | medium-high |
| `esp32` | ESP32 | none | serial only | optional Wi-Fi | low |
| `esp32_plus_raspberry_pi` | ESP32 | Raspberry Pi 4B | CSV | yes | medium |

---

## 7. Recommended Selection

### Fastest MVP

```text
esp32
or
uno_q
```

### Best demo with dashboard

```text
esp32_plus_raspberry_pi
or
uno_q_plus_raspberry_pi
```

### If sensors are not available

```text
Any target is acceptable.
Use simulated inputs first.
```

---

## 8. Common Rules Across All Targets

These must not change by hardware target:

```text
- state machine
- release condition
- default RELEASE_OFF
- safety rules
- JSON Lines schema
- CSV log schema
- event names
- error codes
```

---

## 9. One-Sentence Summary

Use the same control logic and safety interface across all hardware targets; only pin mapping, communication backend, and optional dashboard behavior should differ.
