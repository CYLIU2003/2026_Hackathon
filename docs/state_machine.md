# State Machine

States:

```text
IDLE
BEAR_DETECTED
CONTACT_CONFIRMED
READY_TO_RELEASE
RELEASING
COOLDOWN
ERROR_SAFE
```

Main flow:

```text
IDLE
  ↓ bear_detected
BEAR_DETECTED
  ↓ paw_contact confirmed
CONTACT_CONFIRMED
  ↓ honey enough and system safe
READY_TO_RELEASE
  ↓ start release
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
  ↓ RESET command
IDLE
```

Rules:
- In `ERROR_SAFE`, `release_state` must be `RELEASE_OFF`.
- If `emergency_stop` is true at any time, transition to `ERROR_SAFE`.
- If `honey_amount_percent` is outside 0-100, transition to `ERROR_SAFE`.
- `ERROR_SAFE` must not clear automatically; it only leaves on `RESET`.
