# Interface Spec

## JSON Lines (Arduino Uno -> Raspberry Pi)

One JSON object per line.

Required fields:

```json
{
  "timestamp": "string (ISO-8601 or uptime placeholder)",
  "state": "IDLE | BEAR_DETECTED | CONTACT_CONFIRMED | READY_TO_RELEASE | RELEASING | COOLDOWN | ERROR_SAFE",
  "event": "string",
  "bear_detected": "boolean",
  "paw_contact": "boolean",
  "honey_amount_percent": "integer 0-100",
  "system_safe": "boolean",
  "emergency_stop": "boolean",
  "release_state": "RELEASE_ON | RELEASE_OFF"
}
```

Optional fields:

```json
{
  "previous_state": "string",
  "contact_confirmed": "boolean",
  "raw_contact_value": "number or null",
  "honey_enough": "boolean",
  "release_allowed": "boolean",
  "actuator_open": "boolean",
  "servo_angle": "integer",
  "auto_test_mode": "boolean",
  "error_code": "string or null",
  "error_message": "string or null"
}
```

Notes:
- The MVP uses **simulated inputs**.
- Arduino Uno is the field-side safety controller.
- Until a real-time clock is added, `timestamp` is emitted as uptime like `"T+12345ms"`.

Example:

```json
{"timestamp":"T+5234ms","state":"RELEASING","previous_state":"READY_TO_RELEASE","event":"RELEASE_START","bear_detected":true,"paw_contact":true,"contact_confirmed":true,"raw_contact_value":null,"honey_amount_percent":80,"honey_enough":true,"system_safe":true,"emergency_stop":false,"release_allowed":true,"release_state":"RELEASE_ON","actuator_open":true,"servo_angle":90,"auto_test_mode":true,"error_code":"ERR_NONE","error_message":null}
```

---

## CSV Log (Raspberry Pi)

Columns:

```csv
timestamp,state,previous_state,event,bear_detected,paw_contact,contact_confirmed,raw_contact_value,honey_amount_percent,honey_enough,system_safe,emergency_stop,release_allowed,release_state,actuator_open,servo_angle,auto_test_mode,error_code,error_message
```

Rules:
- Always write the header for a new file.
- Missing optional fields should be written as empty values.

---

## Unified Feeding Decision CSV (Presentation Mirror)

Default path:

```text
data/logs/feeding_decision_log.csv
```

This Raspberry Pi output combines Camera AI and simulated contact-pad inputs
for logging, dashboard display, and integration rehearsal. It is not the
authoritative physical release controller.

Key columns:

```csv
timestamp,input_mode,state,presentation_state,event,camera_status,bear_detected,bear_approaching,confidence,bear_box_area_ratio,contact_detected,contact_confirmed,impedance_kohm,honey_amount_percent,system_safe,emergency_stop,safety_decision,release_state,servo_command,log_status,error_code
```

Presentation aliases:

```text
READY_TO_RELEASE -> SAFE_TO_FEED
RELEASING        -> FEEDING
RELEASE_ON       -> servo_command=RELEASE
RELEASE_OFF      -> servo_command=HOLD
```

On missing/stale Camera AI data, invalid values, emergency stop, or an
exception, the mirror must show `ERROR_SAFE`, `RELEASE_OFF`, and `HOLD`.

---

## Dashboard Demo Mode API

The remote browser reaches the Raspberry Pi dashboard over SSH/Tailscale. The
Raspberry Pi remains the only networked endpoint for Demo Mode, and the Arduino
remains connected by wired USB serial.

HTTP endpoints:

```text
GET  /api/demo-status
GET  /api/demo/status
POST /api/demo-enable       {"enabled":true|false}
POST /api/demo-mode         {"enabled":true|false}
POST /api/demo-command      {"command":"RELEASE|STOP|TEST"}
POST /api/demo-command      {"command":"STOP","emergency_stop":true}
POST /api/demo/release
POST /api/demo/stop
POST /api/demo/test
POST /api/demo/emergency-stop
```

Arduino USB serial command strings:

```text
RELEASE
STOP
TEST
```

Safety rules:

- Default dashboard command state is `STOP` / closed.
- `Release / Open` and `Test Motion` require Demo Mode to be manually enabled
  first.
- `Stop / Close` and `Emergency Stop` are always allowed and send `STOP`.
- If USB serial is unavailable, the dashboard records `SIMULATED` and does not
  control hardware.
- `RELEASE` and `TEST` do not clear Arduino `ERROR_SAFE`; only `RESET` clears
  the error latch.

Demo command CSV:

```csv
timestamp,command,serial_command,demo_enabled,serial_status,result,message,emergency_stop
```
