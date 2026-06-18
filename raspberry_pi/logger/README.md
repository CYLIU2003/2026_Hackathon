# Raspberry Pi Logger

Receives JSON Lines from Arduino Uno and writes CSV logs.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python serial_logger.py --serial-port /dev/ttyACM0 --baudrate 115200 --log-dir ../../data/logs
```

## Output

- CSV logs are saved under `data/logs/`.
- Each run creates a new `log_YYYYMMDD_HHMMSS.csv` file.
- Goda actuator fields such as `actuator_open`, `servo_angle`, and
  `auto_test_mode` are included when the Arduino emits them.
