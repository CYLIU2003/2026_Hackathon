# Raspberry Pi Dashboard

Simple web dashboard showing the latest state from CSV logs.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py --log-dir ../../data/logs --host 0.0.0.0 --port 8080
```

Open `http://<pi-ip>:8080`.
