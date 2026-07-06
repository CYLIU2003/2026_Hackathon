# ESP32 BIA Contact Sensor

This folder contains the optional ESP32 BIA measurement sketch.

The MVP still works without this sensor. Keep Arduino `BIA_INPUT_ENABLED` set
to `0` unless the ESP32 BIA hardware is wired and sending data.

## Wiring to Arduino Uno

| ESP32 BIA side | Arduino Uno side |
|---|---|
| GPIO16 TX | D4 (`PIN_BIA_SERIAL_RX`) |
| GND | GND |

UART settings:

```text
9600 baud, 8N1
ESP32 -> Arduino only
```

GPIO17 is already used as `DDS2_CS`, so it must not be used for the UART TX
line in this sketch.

## Output

ESP32 UART output to Arduino:

```json
{"contact_detected":true,"amplitude1":148.250,"phase1":12.500,"amplitude2":91.000,"phase2":-3.750}
```

ESP32 USB Serial debug output includes `timestamp`, `source`,
`contact_threshold`, and `calibrated` fields.

## USB Serial Commands

Send commands to the ESP32 USB Serial monitor at 115200 baud:

```text
CALIBRATE
SET_THRESHOLD 45.0
STATUS
```

`CALIBRATE` averages 50 no-contact samples and then uses
`baselineAmplitude1 + CALIBRATION_CONTACT_MARGIN` as the contact threshold.

## Safety Notes

- Do not test on real animals.
- Keep BIA measurement low-voltage and low-current.
- Arduino Uno remains the final safety controller.
- If Arduino BIA mode is enabled and BIA data is missing or malformed, Arduino
  enters `ERROR_SAFE` and holds `RELEASE_OFF`.
