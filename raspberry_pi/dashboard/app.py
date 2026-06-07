import argparse
import csv
from pathlib import Path
from typing import Optional

from flask import Flask, render_template_string


HTML_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta http-equiv="refresh" content="{{ refresh_interval }}" />
    <title>Front Paw Contact Pad Dashboard</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 24px; }
      table { border-collapse: collapse; }
      th, td { border: 1px solid #999; padding: 6px 10px; }
      th { background: #f2f2f2; text-align: left; }
    </style>
  </head>
  <body>
    <h2>Front Paw Contact Pad Dashboard</h2>
    {% if log_path %}
      <p><strong>Log file:</strong> {{ log_path }}</p>
    {% endif %}
    {% if row %}
      <table>
        <tr><th>timestamp</th><td>{{ row.get('timestamp') }}</td></tr>
        <tr><th>state</th><td>{{ row.get('state') }}</td></tr>
        <tr><th>event</th><td>{{ row.get('event') }}</td></tr>
        <tr><th>release_state</th><td>{{ row.get('release_state') }}</td></tr>
        <tr><th>bear_detected</th><td>{{ row.get('bear_detected') }}</td></tr>
        <tr><th>paw_contact</th><td>{{ row.get('paw_contact') }}</td></tr>
        <tr><th>honey_amount_percent</th><td>{{ row.get('honey_amount_percent') }}</td></tr>
        <tr><th>system_safe</th><td>{{ row.get('system_safe') }}</td></tr>
        <tr><th>emergency_stop</th><td>{{ row.get('emergency_stop') }}</td></tr>
        <tr><th>error_code</th><td>{{ row.get('error_code') }}</td></tr>
      </table>
    {% else %}
      <p>No log data found yet.</p>
    {% endif %}
  </body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple dashboard for latest log state")
    parser.add_argument("--log-dir", default="data/logs")
    parser.add_argument("--log-file", default="")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--refresh", type=int, default=1)
    return parser.parse_args()


def find_latest_log_file(log_dir: Path) -> Optional[Path]:
    candidates = list(log_dir.glob("*.csv"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_latest_row(log_path: Path) -> Optional[dict]:
    if not log_path.exists():
        return None

    latest = None
    with log_path.open("r", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            latest = row
    return latest


def create_app(log_dir: Path, log_file: str, refresh_interval: int) -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        chosen_log = Path(log_file) if log_file else find_latest_log_file(log_dir)
        row = load_latest_row(chosen_log) if chosen_log else None
        return render_template_string(
            HTML_TEMPLATE,
            row=row,
            log_path=str(chosen_log) if chosen_log else "",
            refresh_interval=refresh_interval,
        )

    return app


def main() -> int:
    args = parse_args()
    log_dir = Path(args.log_dir)
    app = create_app(log_dir, args.log_file, args.refresh)
    app.run(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
