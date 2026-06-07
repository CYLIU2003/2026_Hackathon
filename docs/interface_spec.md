# Interface Spec

## JSON Lines (Arduino Uno Q → Raspberry Pi)

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
  "error_code": "string or null",
  "error_message": "string or null"
}
```

Notes:
- The MVP uses **simulated inputs**.
- Until a real-time clock is added, `timestamp` is emitted as uptime like `"T+12345ms"`.

Example:

```json
{"timestamp":"T+5234ms","state":"RELEASING","previous_state":"READY_TO_RELEASE","event":"RELEASE_START","bear_detected":true,"paw_contact":true,"contact_confirmed":true,"raw_contact_value":null,"honey_amount_percent":80,"honey_enough":true,"system_safe":true,"emergency_stop":false,"release_allowed":true,"release_state":"RELEASE_ON","error_code":"ERR_NONE","error_message":null}
```

---

## CSV Log (Raspberry Pi)

Columns:

```csv
timestamp,state,previous_state,event,bear_detected,paw_contact,contact_confirmed,raw_contact_value,honey_amount_percent,honey_enough,system_safe,emergency_stop,release_allowed,release_state,error_code,error_message
```

Rules:
- Always write the header for a new file.
- Missing optional fields should be written as empty values.
