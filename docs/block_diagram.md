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
[Front Paw Contact Pad]                       |
  - mock input for MVP                        |
  - future resistance / serial input          |
    |                                         |
    +----------------------+------------------+
                           v
              [Safety Decision State Machine]
                - honey amount
                - system safe
                - emergency stop
                - release timeout
                - cooldown
                           |
               +-----------+-----------+
               |                       |
               v                       v
      [RELEASE_ON/OFF]          [CSV + Dashboard]
      Arduino authoritative      Raspberry Pi demo mirror
```

Notes:
- Arduino Uno is the **main safety controller**.
- Raspberry Pi may mirror the decision for presentation, logging, and
  integration testing, but it does not directly drive the physical actuator.
- Default state is always **RELEASE_OFF**.
- The MVP contact input is simulated and can later be replaced with Arduino
  serial resistance/contact data.
