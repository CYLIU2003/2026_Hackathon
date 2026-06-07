# Block Diagram

This diagram shows the MVP data flow and responsibility split.

```text
[Simulated Bear]
    |
    v
[Front Paw Contact Pad Inputs]  (simulated)
    |
    v
[Arduino Uno Q]
  - simulated inputs
  - state machine
  - release decision logic
  - RELEASE_ON / RELEASE_OFF output
  - JSON Lines over serial
    |
    v
[Raspberry Pi 4B]
  - receive JSON Lines
  - CSV logging
  - simple dashboard
    |
    v
[Demo / Presentation]
```

Notes:
- Arduino Uno Q is the **main safety controller**.
- Raspberry Pi is **logging and visualization only**.
- Default state is always **RELEASE_OFF**.
