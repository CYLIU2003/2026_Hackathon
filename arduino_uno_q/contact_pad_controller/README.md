# Contact Pad Controller (Arduino Uno Q)

This sketch runs the MVP state machine using simulated inputs.

## Build

1. Open `contact_pad_controller.ino` in Arduino IDE.
2. Select the Arduino Uno Q board.
3. Upload the sketch.
4. Open the serial monitor at **115200 baud**.

## Behavior

- Release signal is **RELEASE_ON** only when all safety conditions are met.
- On error or emergency stop, it stays **RELEASE_OFF**.
