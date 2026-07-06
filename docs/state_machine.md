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
  ↓ bear_approaching and paw_contact confirmed
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

Presentation aliases:

```text
READY_TO_RELEASE -> SAFE_TO_FEED
RELEASING        -> FEEDING
CSV write        -> log_status=SAVED
```

`LOGGED` is not a physical control state because logging must not delay or
change the fail-safe release state machine.

Error path:

```text
ANY_STATE
  ↓ emergency_stop / invalid input / BIA timeout / bad BIA message / internal error
ERROR_SAFE
  ↓ RESET command
IDLE
```

Rules:
- In `ERROR_SAFE`, `release_state` must be `RELEASE_OFF`.
- If `emergency_stop` is true at any time, transition to `ERROR_SAFE`.
- If `honey_amount_percent` is outside 0-100, transition to `ERROR_SAFE`.
- If BIA UART input is enabled and data is missing, stale, too long, or
  malformed, transition to `ERROR_SAFE`.
- `ERROR_SAFE` must not clear automatically; it only leaves on `RESET`.
- The Raspberry Pi demo mirror may issue a software reset after healthy Camera
  AI data returns. This does not reset or command the Arduino controller.
