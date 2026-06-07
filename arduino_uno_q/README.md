# Arduino Uno Q - Contact Pad Controller

This module runs the MVP state machine with **simulated inputs**.

## Files

- `contact_pad_controller/contact_pad_controller.ino` - main controller
- `contact_pad_controller/config.h` - configuration constants

## How to Run

1. Open the sketch in Arduino IDE.
2. Select the Arduino Uno Q board.
3. Upload the sketch.
4. Open the serial monitor at **115200 baud**.
5. If the controller enters `ERROR_SAFE`, send `RESET` on a new line to recover.

## Output

- `RELEASE_ON` / `RELEASE_OFF` is emitted via:
  - `PIN_RELEASE_SIGNAL`
  - `PIN_RELEASE_LED`
- JSON Lines are printed to serial.
- `ERROR_SAFE` stays latched until a `RESET` command is received over serial.

## Notes

- Inputs are **simulated** using a timed scenario.
- `timestamp` is uptime (`T+<ms>`) until a real-time clock is added.
