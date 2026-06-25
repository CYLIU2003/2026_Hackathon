# Feeding Safety Decision Mirror

This Raspberry Pi process combines Camera AI output with simulated contact-pad
inputs and writes a unified CSV for the presentation dashboard.

It is a **non-authoritative demo mirror**. The Arduino Uno Q remains responsible
for the physical `RELEASE_ON / RELEASE_OFF` safety decision.

```bash
python -m raspberry_pi.safety_control.safety_controller \
  --input-mode camera \
  --camera-log-file data/logs/camera_ai_log.csv \
  --output data/logs/feeding_decision_log.csv \
  --mock-contact \
  --mock-impedance-kohm 92.4
```

The current prototype uses simulated sensor inputs. Replace the mock contact
arguments with parsed Arduino serial values when the real contact sensor is
ready.

For a camera-free presentation rehearsal:

```bash
python -m raspberry_pi.safety_control.safety_controller \
  --input-mode scenario \
  --output data/logs/feeding_decision_log.csv
```
