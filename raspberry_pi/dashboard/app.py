import argparse
import csv
import time
from pathlib import Path
from typing import Optional

from flask import Flask, abort, render_template_string, send_file


HTML_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta http-equiv="refresh" content="{{ refresh_interval }}" />
    <title>Front Paw Contact Pad Dashboard</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f7f8fa;
        --panel: #ffffff;
        --border: #d8dde6;
        --text: #172033;
        --muted: #667085;
        --ok: #0b7a53;
        --warn: #b54708;
        --error: #b42318;
      }
      * { box-sizing: border-box; }
      body {
        font-family: Arial, sans-serif;
        margin: 0;
        background: var(--bg);
        color: var(--text);
      }
      header {
        padding: 18px 24px;
        border-bottom: 1px solid var(--border);
        background: var(--panel);
      }
      h1 { font-size: 22px; margin: 0 0 4px; }
      h2 { font-size: 17px; margin: 0 0 12px; }
      main {
        display: grid;
        grid-template-columns: minmax(320px, 1.5fr) minmax(280px, 1fr);
        gap: 16px;
        padding: 16px;
      }
      section {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 16px;
      }
      table { border-collapse: collapse; width: 100%; }
      th, td {
        border-top: 1px solid var(--border);
        padding: 7px 8px;
        text-align: left;
        vertical-align: top;
      }
      th { color: var(--muted); font-weight: 600; width: 42%; }
      .muted { color: var(--muted); }
      .camera-frame {
        width: 100%;
        max-height: 68vh;
        object-fit: contain;
        background: #111827;
        border: 1px solid var(--border);
        border-radius: 6px;
      }
      .placeholder {
        display: grid;
        min-height: 260px;
        place-items: center;
        background: #111827;
        color: #ffffff;
        border-radius: 6px;
        text-align: center;
        padding: 20px;
      }
      .pill {
        display: inline-block;
        min-width: 74px;
        border-radius: 999px;
        padding: 3px 8px;
        text-align: center;
        font-size: 12px;
        font-weight: 700;
        border: 1px solid var(--border);
      }
      .ok { color: var(--ok); }
      .warn { color: var(--warn); }
      .error { color: var(--error); }
      .decision {
        grid-column: 1 / -1;
        border-left: 6px solid var(--ok);
      }
      .decision-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(150px, 1fr));
        gap: 10px;
      }
      .decision-item {
        border: 1px solid var(--border);
        border-radius: 7px;
        padding: 10px;
      }
      .decision-label {
        color: var(--muted);
        font-size: 12px;
        margin-bottom: 5px;
      }
      .decision-value {
        font-size: 17px;
        font-weight: 700;
        overflow-wrap: anywhere;
      }
      @media (max-width: 860px) {
        main { grid-template-columns: 1fr; padding: 12px; }
        .decision-grid { grid-template-columns: 1fr 1fr; }
      }
    </style>
  </head>
  <body>
    <header>
      <h1>Front Paw Contact Pad Dashboard</h1>
      <div class="muted">Remote monitor for Camera AI, contact-pad state, and fail-safe release status.</div>
    </header>
    <main>
      <section class="decision">
        <h2>Feeding Safety Decision</h2>
        {% if row %}
          <div class="decision-grid">
            <div class="decision-item">
              <div class="decision-label">Current State</div>
              <div class="decision-value">{{ row.get('presentation_state', row.get('state', '-')) }}</div>
            </div>
            <div class="decision-item">
              <div class="decision-label">Camera Status</div>
              <div class="decision-value">{{ row.get('camera_status', '-') }}</div>
            </div>
            <div class="decision-item">
              <div class="decision-label">Bear Detection</div>
              <div class="decision-value">{{ row.get('bear_detected', '-') }}</div>
            </div>
            <div class="decision-item">
              <div class="decision-label">Confidence</div>
              <div class="decision-value">{{ row.get('confidence', '-') }}</div>
            </div>
            <div class="decision-item">
              <div class="decision-label">Contact Pad</div>
              <div class="decision-value">{{ 'Confirmed' if truthy(row.get('contact_confirmed')) else 'Waiting' }}</div>
            </div>
            <div class="decision-item">
              <div class="decision-label">Safety Decision</div>
              <div class="decision-value">{{ row.get('safety_decision', row.get('event', '-')) }}</div>
            </div>
            <div class="decision-item">
              <div class="decision-label">Servo Command</div>
              <div class="decision-value">{{ row.get('servo_command', row.get('release_state', 'HOLD')) }}</div>
            </div>
            <div class="decision-item">
              <div class="decision-label">CSV Log</div>
              <div class="decision-value">{{ row.get('log_status', 'SAVED') }}</div>
            </div>
            <div class="decision-item">
              <div class="decision-label">Input Mode</div>
              <div class="decision-value">{{ row.get('input_mode', 'ARDUINO_SERIAL') }}</div>
            </div>
          </div>
        {% else %}
          <p>No integrated safety-decision data found yet. Output remains HOLD.</p>
        {% endif %}
      </section>

      <section>
        <h2>Camera AI View</h2>
        {% if camera_frame_available %}
          <img
            class="camera-frame"
            src="{{ url_for('camera_frame') }}?t={{ cache_buster }}"
            alt="Latest annotated Camera AI frame"
          />
        {% else %}
          <div class="placeholder">
            <div>
              <strong>No camera frame yet</strong><br />
              Start Camera AI with debug frames enabled.
            </div>
          </div>
        {% endif %}
        <p class="muted">Frame: {{ camera_frame_path }}</p>
      </section>

      <section>
        <h2>Camera AI State</h2>
        {% if camera_row %}
          <table>
            <tr><th>timestamp</th><td>{{ camera_row.get('timestamp') }}</td></tr>
            <tr><th>event</th><td>{{ camera_row.get('event') }}</td></tr>
            <tr><th>ai_camera_ok</th><td>{{ status_pill(camera_row.get('ai_camera_ok'))|safe }}</td></tr>
            <tr><th>ai_model_ok</th><td>{{ status_pill(camera_row.get('ai_model_ok'))|safe }}</td></tr>
            <tr><th>ai_bear_detected</th><td>{{ status_pill(camera_row.get('ai_bear_detected'))|safe }}</td></tr>
            <tr><th>ai_bear_approaching</th><td>{{ status_pill(camera_row.get('ai_bear_approaching'))|safe }}</td></tr>
            <tr><th>ai_bear_confidence</th><td>{{ camera_row.get('ai_bear_confidence') }}</td></tr>
            <tr><th>ai_bear_box_area_ratio</th><td>{{ camera_row.get('ai_bear_box_area_ratio') }}</td></tr>
            <tr><th>inference_time_ms</th><td>{{ camera_row.get('inference_time_ms') }}</td></tr>
            <tr><th>camera_device</th><td>{{ camera_row.get('camera_device') }}</td></tr>
          </table>
        {% else %}
          <p>No Camera AI log data found yet.</p>
        {% endif %}
        <p class="muted">Camera log: {{ camera_log_path }}</p>
      </section>

      <section>
        <h2>Safety Control Details</h2>
        {% if row %}
          <table>
            <tr><th>timestamp</th><td>{{ row.get('timestamp') }}</td></tr>
            <tr><th>state</th><td>{{ row.get('state') }}</td></tr>
            <tr><th>event</th><td>{{ row.get('event') }}</td></tr>
            <tr><th>release_state</th><td>{{ row.get('release_state') }}</td></tr>
            <tr><th>bear_detected</th><td>{{ row.get('bear_detected') }}</td></tr>
            <tr><th>bear_approaching</th><td>{{ row.get('bear_approaching', '') }}</td></tr>
            <tr><th>contact_detected</th><td>{{ row.get('contact_detected', row.get('paw_contact', '')) }}</td></tr>
            <tr><th>contact_confirmed</th><td>{{ row.get('contact_confirmed', '') }}</td></tr>
            <tr><th>impedance_kohm</th><td>{{ row.get('impedance_kohm', row.get('raw_contact_value', '')) }}</td></tr>
            <tr><th>honey_amount_percent</th><td>{{ row.get('honey_amount_percent') }}</td></tr>
            <tr><th>system_safe</th><td>{{ row.get('system_safe') }}</td></tr>
            <tr><th>emergency_stop</th><td>{{ row.get('emergency_stop') }}</td></tr>
            <tr><th>error_code</th><td>{{ row.get('error_code') }}</td></tr>
          </table>
        {% else %}
          <p>No contact-pad log data found yet.</p>
        {% endif %}
        <p class="muted">Contact log: {{ log_path }}</p>
      </section>
    </main>
  </body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple dashboard for latest log state")
    parser.add_argument("--log-dir", default="data/logs")
    parser.add_argument("--log-file", default="")
    parser.add_argument("--camera-log-file", default="data/logs/camera_ai_log.csv")
    parser.add_argument("--debug-frame-dir", default="data/debug_frames")
    parser.add_argument("--camera-frame-file", default="latest_camera_ai.jpg")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--refresh", type=int, default=1)
    return parser.parse_args()


def find_latest_log_file(
    log_dir: Path,
    *,
    excluded_names: Optional[set[str]] = None,
) -> Optional[Path]:
    excluded_names = excluded_names or set()
    candidates = list(log_dir.glob("*.csv"))
    candidates = [path for path in candidates if path.name not in excluded_names]
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


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def status_pill(value: object) -> str:
    if value is None or value == "":
        return '<span class="pill warn">unknown</span>'
    css_class = "ok" if truthy(value) else "error"
    label = "true" if truthy(value) else "false"
    return f'<span class="pill {css_class}">{label}</span>'


def create_app(
    log_dir: Path,
    log_file: str,
    refresh_interval: int,
    *,
    camera_log_file: str,
    debug_frame_dir: Path,
    camera_frame_file: str,
) -> Flask:
    app = Flask(__name__)
    app.jinja_env.globals["status_pill"] = status_pill
    app.jinja_env.globals["truthy"] = truthy
    log_dir = log_dir.resolve()
    debug_frame_dir = debug_frame_dir.resolve()
    resolved_log_file = str(Path(log_file).resolve()) if log_file else ""
    resolved_camera_log_file = str(Path(camera_log_file).resolve())

    @app.route("/")
    def index():
        chosen_camera_log = Path(resolved_camera_log_file)
        chosen_log = (
            Path(resolved_log_file)
            if resolved_log_file
            else find_latest_log_file(
                log_dir,
                excluded_names={chosen_camera_log.name},
            )
        )
        row = load_latest_row(chosen_log) if chosen_log else None
        camera_row = load_latest_row(chosen_camera_log) if chosen_camera_log else None
        camera_frame_path = debug_frame_dir / camera_frame_file
        return render_template_string(
            HTML_TEMPLATE,
            row=row,
            log_path=str(chosen_log) if chosen_log else "",
            camera_row=camera_row,
            camera_log_path=str(chosen_camera_log) if chosen_camera_log else "",
            camera_frame_path=str(camera_frame_path),
            camera_frame_available=camera_frame_path.exists(),
            cache_buster=time.time_ns(),
            refresh_interval=refresh_interval,
        )

    @app.route("/camera/latest.jpg")
    def camera_frame():
        camera_frame_path = debug_frame_dir / camera_frame_file
        if not camera_frame_path.exists():
            abort(404)
        response = send_file(
            camera_frame_path,
            mimetype="image/jpeg",
            conditional=False,
            max_age=0,
        )
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return app


def main() -> int:
    args = parse_args()
    log_dir = Path(args.log_dir)
    app = create_app(
        log_dir,
        args.log_file,
        args.refresh,
        camera_log_file=args.camera_log_file,
        debug_frame_dir=Path(args.debug_frame_dir),
        camera_frame_file=args.camera_frame_file,
    )
    app.run(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
