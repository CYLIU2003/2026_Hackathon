# Block Diagram

This diagram shows the MVP data flow and responsibility split.

```text
[USB Camera]
    |
    v
[YOLO Bear Detection]
  - confidence
  - bounding-box area as distance proxy
  - consecutive detection check
    |
    v
[Bear Approach Signal] ----------------------+
                                              |
[Front Paw Contact Input]                     |
  - simulated input for MVP                   |
  - optional ESP32 BIA UART input             |
    |                                         |
    +----------------------+------------------+
                           v
              [Arduino Uno Safety State Machine]
                - honey amount
                - system safe
                - emergency stop
                - BIA timeout / bad message check
                - release timeout
                - cooldown
                           |
               +-----------+-----------+
               |                       |
               v                       v
      [RELEASE_ON/OFF]          [CSV + Dashboard]
      Arduino authoritative      Raspberry Pi demo mirror
```

Optional BIA contact path:

```text
[ESP32 + AD9833 BIA Measurement]
  - amplitude / phase measurement
  - contact_detected threshold
  - no final release authority
        |
        | UART JSON Lines, 9600 baud
        | ESP32 GPIO16 TX -> Arduino D4 RX
        v
[Arduino Uno Safety State Machine]
  - confirms contact duration
  - applies honey / safety / emergency-stop checks
  - defaults to RELEASE_OFF on stale or invalid BIA data
```

Notes:
- Arduino Uno is the **main safety controller**.
- Raspberry Pi may mirror the decision for presentation, logging, and
  integration testing, but it does not directly drive the physical actuator.
- Default state is always **RELEASE_OFF**.
- The MVP contact input is simulated. BIA UART input is optional and must be
  enabled explicitly in `config.h`.
