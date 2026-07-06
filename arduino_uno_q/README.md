# Arduino Uno - Contact Pad Controller

This module runs the MVP state machine with **simulated inputs** by default.
It can optionally receive ESP32 BIA contact data over UART.

The directory name is kept for repository compatibility, but the current sketch
targets a standard **Arduino Uno**.

## Files

- `contact_pad_controller/contact_pad_controller.ino` - main controller
- `contact_pad_controller/config.h` - configuration constants

## How to Run

1. Open the sketch in Arduino IDE.
2. Select **Arduino Uno** as the board.
3. Upload the sketch.
4. Open the serial monitor at **115200 baud**.
5. If the controller enters `ERROR_SAFE`, send `RESET` on a new line to recover.

## Optional ESP32 BIA Input

The default build keeps BIA disabled:

```c
#define BIA_INPUT_ENABLED 0
```

To test the ESP32 BIA contact path, set it to `1` in
`contact_pad_controller/config.h`, then wire:

| ESP32 BIA side | Arduino Uno side |
|---|---|
| GPIO16 TX | D4 (`PIN_BIA_SERIAL_RX`) |
| GND | GND |

The UART link is ESP32-to-Arduino only at **9600 baud**. If the target board
has a suitable hardware `Serial1`, set `BIA_USE_HARDWARE_SERIAL1` to `1` and
wire according to that board's RX pin instead.

When BIA input is enabled, missing or malformed BIA data enters `ERROR_SAFE`
and keeps `RELEASE_OFF`.

## Output

- `RELEASE_ON` / `RELEASE_OFF` is emitted via:
  - `PIN_RELEASE_SIGNAL`
  - `PIN_RELEASE_LED`
- JSON Lines are printed to serial.
- `ERROR_SAFE` stays latched until a `RESET` command is received over serial.

## Notes

- Inputs are **simulated** using a timed scenario.
- This prototype uses simulated sensor inputs unless `BIA_INPUT_ENABLED` is
  explicitly changed.
- `timestamp` is uptime (`T+<ms>`) until a real-time clock is added.
