import argparse
import csv
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template_string,
    request,
    send_file,
    url_for,
)

try:
    from .motor_driver import DriverConfig, MotorDriverController
except ImportError:
    from motor_driver import DriverConfig, MotorDriverController


JST = timezone(timedelta(hours=9))

DEMO_COMMAND_ALIASES = {
    "RELEASE": ("RELEASE", "RELEASE"),
    "OPEN": ("RELEASE", "RELEASE"),
    "STOP": ("STOP", "STOP"),
    "CLOSE": ("STOP", "STOP"),
    "TEST": ("TEST", "TEST"),
    "TEST_MOTION": ("TEST", "TEST"),
    "EMERGENCY_STOP": ("EMERGENCY_STOP", "STOP"),
    "ESTOP": ("EMERGENCY_STOP", "STOP"),
}
DEMO_COMMANDS_REQUIRING_ENABLE = {"RELEASE", "TEST"}
DEMO_COMMAND_FIELDNAMES = [
    "timestamp",
    "command",
    "serial_command",
    "demo_enabled",
    "serial_status",
    "result",
    "message",
    "emergency_stop",
]


HTML_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
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
        --action: #175cd3;
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
      .demo {
        grid-column: 1 / -1;
        border-left: 6px solid var(--action);
      }
      .connection {
        grid-column: 1 / -1;
        border-left: 6px solid #7c3aed;
      }
      .connection-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }
      .connection-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .connection-card {
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px;
        background: #f9fafb;
      }
      .connection-card h3 {
        margin: 0 0 8px;
        font-size: 14px;
        color: var(--muted);
      }
      .connection-card .value {
        font-size: 18px;
        font-weight: 700;
      }
      .form-group {
        margin-bottom: 12px;
      }
      .form-group label {
        display: block;
        font-size: 13px;
        font-weight: 600;
        color: var(--muted);
        margin-bottom: 4px;
      }
      .form-group input,
      .form-group select {
        width: 100%;
        padding: 8px;
        border: 1px solid var(--border);
        border-radius: 6px;
        font-size: 14px;
      }
      .form-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
      }
      .ok { color: var(--ok); }
      .warn { color: var(--warn); }
      .error { color: var(--error); }
      .decision {
        grid-column: 1 / -1;
        border-left: 6px solid var(--ok);
      }
      .demo {
        grid-column: 1 / -1;
        border-left: 6px solid var(--action);
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
      .demo-top,
      .demo-controls {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
      }
      .demo-top {
        justify-content: space-between;
        margin-bottom: 12px;
      }
      .demo-controls { margin-bottom: 14px; }
      .button {
        min-height: 38px;
        border: 1px solid var(--border);
        border-radius: 7px;
        padding: 8px 12px;
        background: #ffffff;
        color: var(--text);
        font-weight: 700;
        cursor: pointer;
      }
      .button.primary {
        background: var(--action);
        border-color: var(--action);
        color: #ffffff;
      }
      .button.danger {
        background: var(--error);
        border-color: var(--error);
        color: #ffffff;
      }
      .button:disabled {
        cursor: not-allowed;
        opacity: 0.45;
      }
      .demo-status-table th { width: 24%; }
      @media (max-width: 860px) {
        main { grid-template-columns: 1fr; padding: 12px; }
        .decision-grid { grid-template-columns: 1fr 1fr; }
      }
      @media (max-width: 520px) {
        .decision-grid { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <header>
      <h1>Front Paw Contact Pad Dashboard</h1>
      <div class="muted">Remote monitor for Camera AI, contact-pad state, and fail-safe release status.</div>
    </header>
    <main id="dashboard-main"
          data-refresh-interval="{{ refresh_interval }}"
          data-demo-enabled="{{ '1' if demo_status.get('demo_enabled') else '0' }}"
          data-emergency-stop="{{ '1' if demo_status.get('emergency_stop') else '0' }}">
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

      <section class="demo">
        <h2>Demo Mode</h2>
        <div class="demo-top">
          <div>
            {% if demo_status.get('demo_enabled') %}
              <span class="pill ok">ENABLED</span>
            {% else %}
              <span class="pill warn">DISABLED</span>
            {% endif %}
            <span class="muted">Default command: STOP / closed</span>
          </div>
          <form action="{{ url_for('demo_mode') }}" method="post" data-demo-control>
            {% if demo_status.get('demo_enabled') %}
              <button class="button" type="submit" name="enabled" value="false">Disable Demo Mode</button>
            {% else %}
              <button class="button primary" type="submit" name="enabled" value="true">Enable Demo Mode</button>
            {% endif %}
          </form>
        </div>

        <div class="demo-controls">
          <form action="{{ url_for('demo_command') }}" method="post" data-demo-control>
            <input type="hidden" name="command" value="RELEASE" />
            <button class="button primary" type="submit" {% if not demo_status.get('demo_enabled') %}disabled{% endif %}>
              Release / Open
            </button>
          </form>
          <form action="{{ url_for('demo_command') }}" method="post" data-demo-control>
            <input type="hidden" name="command" value="STOP" />
            <button class="button" type="submit">Stop / Close</button>
          </form>
          <form action="{{ url_for('demo_command') }}" method="post" data-demo-control>
            <input type="hidden" name="command" value="TEST" />
            <button class="button" type="submit" {% if not demo_status.get('demo_enabled') %}disabled{% endif %}>
              Test Motion
            </button>
          </form>
          <form action="{{ url_for('demo_command') }}" method="post" data-demo-control>
            <input type="hidden" name="command" value="EMERGENCY_STOP" />
            <button class="button danger" type="submit">Emergency Stop</button>
          </form>
        </div>

        <table class="demo-status-table">
          <tr><th>Last command sent</th><td>{{ demo_status.get('last_command', 'STOP') }}</td></tr>
          <tr><th>Command timestamp</th><td>{{ demo_status.get('command_timestamp') or '-' }}</td></tr>
          <tr><th>Serial connection status</th><td>{{ demo_status.get('serial_status', 'NOT_CONNECTED') }}</td></tr>
          <tr><th>Result</th><td>{{ demo_status.get('result', '-') }}</td></tr>
          <tr><th>Message</th><td>{{ demo_status.get('message', '-') }}</td></tr>
        </table>
        <p class="muted">Demo command log: {{ demo_status.get('log_path', '') }}</p>
      </section>

      <section class="connection">
        <h2>Direct Motor Driver Portal</h2>
        <div class="connection-header">
          <div>
            {% if motor_status.get('connected') %}
              <span class="pill ok">CONNECTED</span>
            {% elif motor_status.get('emergency_stop') %}
              <span class="pill error">EMERGENCY STOP</span>
            {% else %}
              <span class="pill warn">DISCONNECTED</span>
            {% endif %}
            <span class="muted">Mode: {{ motor_status.get('motor_mode', 'SIMULATION') }}</span>
          </div>
          <div>
            <form action="{{ url_for('motor_test') }}" method="post" style="display: inline;">
              <button class="button" type="submit">Test Connection</button>
            </form>
            {% if motor_status.get('emergency_stop') %}
              <form action="{{ url_for('motor_reset') }}" method="post" style="display: inline;">
                <button class="button primary" type="submit">Reset</button>
              </form>
            {% else %}
              <form action="{{ url_for('motor_emergency_stop') }}" method="post" style="display: inline;">
                <button class="button danger" type="submit">Emergency Stop</button>
              </form>
            {% endif %}
          </div>
        </div>

        <div class="connection-grid">
          <div class="connection-card">
            <h3>Motor State</h3>
            <div class="value">{{ motor_status.get('motor_state', 'CLOSED') }}</div>
          </div>
          <div class="connection-card">
            <h3>Current Angle</h3>
            <div class="value">{{ motor_status.get('current_angle', 0) }}°</div>
          </div>
          <div class="connection-card">
            <h3>Operation Count</h3>
            <div class="value">{{ motor_status.get('operation_count', 0) }}</div>
          </div>
          <div class="connection-card">
            <h3>Last Operation</h3>
            <div class="value">{{ motor_status.get('last_operation', '-') }}</div>
            <div class="muted">{{ motor_status.get('last_operation_timestamp', '-') }}</div>
          </div>
        </div>

        {% if motor_status.get('error_message') %}
          <div style="background: #fee; border: 1px solid var(--error); border-radius: 6px; padding: 10px; margin-bottom: 16px;">
            <strong class="error">Error:</strong> {{ motor_status.get('error_message') }}
          </div>
        {% endif %}

        <div class="demo-controls">
          <form action="{{ url_for('motor_open') }}" method="post">
            <button class="button primary" type="submit" {% if motor_status.get('emergency_stop') %}disabled{% endif %}>
              Open Motor
            </button>
          </form>
          <form action="{{ url_for('motor_close') }}" method="post">
            <button class="button" type="submit" {% if motor_status.get('emergency_stop') %}disabled{% endif %}>
              Close Motor
            </button>
          </form>
        </div>

        <h3 style="margin-top: 20px;">Configuration</h3>
        <form action="{{ url_for('motor_config') }}" method="post">
          <div class="form-row">
            <div class="form-group">
              <label for="motor_mode">Motor Mode</label>
              <select id="motor_mode" name="motor_mode">
                <option value="SIMULATION" {% if motor_config.get('motor_mode') == 'SIMULATION' %}selected{% endif %}>SIMULATION</option>
                <option value="PCA9685_SERVO" {% if motor_config.get('motor_mode') == 'PCA9685_SERVO' %}selected{% endif %}>PCA9685_SERVO</option>
                <option value="L293D_STEPPER" {% if motor_config.get('motor_mode') == 'L293D_STEPPER' %}selected{% endif %}>L293D_STEPPER</option>
              </select>
            </div>
            <div class="form-group">
              <label for="pca9685_i2c_address">PCA9685 I2C Address</label>
              <input type="number" id="pca9685_i2c_address" name="pca9685_i2c_address" value="{{ motor_config.get('pca9685_i2c_address', 112) }}" />
            </div>
            <div class="form-group">
              <label for="pca9685_i2c_bus">I2C Bus</label>
              <input type="number" id="pca9685_i2c_bus" name="pca9685_i2c_bus" value="{{ motor_config.get('pca9685_i2c_bus', 1) }}" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="pca9685_servo_channel">Servo Channel</label>
              <input type="number" id="pca9685_servo_channel" name="pca9685_servo_channel" value="{{ motor_config.get('pca9685_servo_channel', 0) }}" />
            </div>
            <div class="form-group">
              <label for="pca9685_servo_open_angle">Open Angle (°)</label>
              <input type="number" id="pca9685_servo_open_angle" name="pca9685_servo_open_angle" value="{{ motor_config.get('pca9685_servo_open_angle', 90) }}" />
            </div>
            <div class="form-group">
              <label for="pca9685_servo_closed_angle">Closed Angle (°)</label>
              <input type="number" id="pca9685_servo_closed_angle" name="pca9685_servo_closed_angle" value="{{ motor_config.get('pca9685_servo_closed_angle', 0) }}" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="l293d_stepper_open_steps">Stepper Open Steps</label>
              <input type="number" id="l293d_stepper_open_steps" name="l293d_stepper_open_steps" value="{{ motor_config.get('l293d_stepper_open_steps', 50) }}" />
            </div>
            <div class="form-group">
              <label for="l293d_stepper_step_delay_ms">Step Delay (ms)</label>
              <input type="number" id="l293d_stepper_step_delay_ms" name="l293d_stepper_step_delay_ms" value="{{ motor_config.get('l293d_stepper_step_delay_ms', 5) }}" />
            </div>
            <div class="form-group">
              <label for="l293d_release_coils_after_move">Release Coils After Move</label>
              <select id="l293d_release_coils_after_move" name="l293d_release_coils_after_move">
                <option value="true" {% if motor_config.get('l293d_release_coils_after_move') %}selected{% endif %}>Yes</option>
                <option value="false" {% if not motor_config.get('l293d_release_coils_after_move') %}selected{% endif %}>No</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="max_operation_duration_ms">Max Operation Duration (ms)</label>
              <input type="number" id="max_operation_duration_ms" name="max_operation_duration_ms" value="{{ motor_config.get('max_operation_duration_ms', 5000) }}" />
            </div>
            <div class="form-group">
              <label for="cooldown_after_operation_ms">Cooldown After Operation (ms)</label>
              <input type="number" id="cooldown_after_operation_ms" name="cooldown_after_operation_ms" value="{{ motor_config.get('cooldown_after_operation_ms', 2000) }}" />
            </div>
          </div>

          <button class="button primary" type="submit">Save Configuration</button>
        </form>

        <h3 style="margin-top: 20px;">Hardware Status</h3>
        <table>
          <tr><th>I2C Available</th><td>{{ status_pill(motor_status.get('i2c_available'))|safe }}</td></tr>
          <tr><th>GPIO Available</th><td>{{ status_pill(motor_status.get('gpio_available'))|safe }}</td></tr>
          <tr><th>Driver Available</th><td>{{ status_pill(motor_status.get('driver_available'))|safe }}</td></tr>
        </table>
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
    <script>
      (function () {
        var main = document.getElementById("dashboard-main");
        if (!main) { return; }
        var refreshInterval = parseInt(
          main.getAttribute("data-refresh-interval") || "2", 10
        );
        if (!isFinite(refreshInterval) || refreshInterval < 1) {
          refreshInterval = 2;
        }
        var lastEstop = main.getAttribute("data-emergency-stop") === "1";
        var fetching = false;

        function refreshMain() {
          if (fetching) { return; }
          fetching = true;
          fetch("/", { headers: { "X-Dashboard-Partial": "1" }, credentials: "same-origin" })
            .then(function (response) {
              if (!response.ok) { throw new Error("HTTP " + response.status); }
              return response.text();
            })
            .then(function (html) {
              var doc = new DOMParser().parseFromString(html, "text/html");
              var newMain = doc.getElementById("dashboard-main");
              if (newMain) {
                main.innerHTML = newMain.innerHTML;
                // Re-run inline scripts inside the fetched content.
                newMain.querySelectorAll("script").forEach(function (oldScript) {
                  var script = document.createElement("script");
                  if (oldScript.src) {
                    script.src = oldScript.src;
                  } else {
                    script.textContent = oldScript.textContent;
                  }
                  main.appendChild(script);
                  script.remove();
                });
                var estop = main.getAttribute("data-emergency-stop") === "1";
                lastEstop = estop;
              }
            })
            .catch(function () { /* ignore transient fetch errors */ })
            .finally(function () { fetching = false; });
        }

        function submitForm(form) {
          var enabled = main.getAttribute("data-demo-enabled") === "1";
          var estop = main.getAttribute("data-emergency-stop") === "1";
          var inputs = form.querySelectorAll(
            'input:not([type="submit"]):not([type="button"]):not([type="reset"])'
          );
          var hasRequireEnable = !!form.querySelector(
            'input[name="command"][value="RELEASE"], input[name="command"][value="TEST"]'
          );
          if (hasRequireEnable && !enabled) {
            return Promise.resolve(false);
          }
          var payload = new URLSearchParams();
          inputs.forEach(function (input) {
            if (input.name) { payload.append(input.name, input.value); }
          });
          return fetch(form.getAttribute("action") || form.action, {
            method: form.method || "POST",
            body: payload,
            credentials: "same-origin",
            headers: { "Content-Type": "application/x-www-form-urlencoded" }
          }).then(function () { return true; }).catch(function () { return false; });
        }

        function bindForms(root) {
          var forms = root.querySelectorAll('form[data-demo-control]');
          forms.forEach(function (form) {
            form.addEventListener("submit", function (event) {
              event.preventDefault();
              var btn = form.querySelector('button[type="submit"]');
              if (btn) { btn.disabled = true; }
              submitForm(form).then(function () {
                refreshMain();
                setTimeout(function () {
                  if (btn) { btn.disabled = false; }
                }, 300);
              });
            });
          });
        }

        document.addEventListener("submit", function (event) {
          var form = event.target;
          if (form && form.hasAttribute('data-demo-control')) {
            event.preventDefault();
            var btn = form.querySelector('button[type="submit"]');
            if (btn) { btn.disabled = true; }
            submitForm(form).then(function () {
              refreshMain();
              setTimeout(function () {
                if (btn) { btn.disabled = false; }
              }, 300);
            });
          }
        });

        bindForms(document);
        setInterval(refreshMain, refreshInterval * 1000);
      })();
    </script>
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
    parser.add_argument("--demo-serial-port", default="/dev/ttyACM0")
    parser.add_argument("--demo-baudrate", type=int, default=115200)
    parser.add_argument("--demo-command-log-file", default="data/logs/demo_commands.csv")
    parser.add_argument("--demo-serial-timeout", type=float, default=1.0)
    parser.add_argument("--demo-serial-reset-delay", type=float, default=2.0)
    parser.add_argument("--demo-force-simulation", action="store_true")
    parser.add_argument("--motor-driver-config", default="config.motor_driver.json")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--refresh", type=int, default=2)
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


def now_jst_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def normalize_demo_command(raw_command: object) -> tuple[Optional[str], Optional[str]]:
    command = str(raw_command or "").strip().upper()
    return DEMO_COMMAND_ALIASES.get(command, (None, None))


def default_serial_client_factory(
    port: str,
    baudrate: int,
    timeout: float,
    write_timeout: float,
):
    import serial  # type: ignore

    if "://" in port:
        return serial.serial_for_url(
            port,
            baudrate=baudrate,
            timeout=timeout,
            write_timeout=write_timeout,
        )
    return serial.Serial(
        port=port,
        baudrate=baudrate,
        timeout=timeout,
        write_timeout=write_timeout,
    )


class DemoCommandService:
    def __init__(
        self,
        *,
        serial_port: str,
        baudrate: int,
        command_log_file: Path,
        serial_timeout: float,
        serial_reset_delay: float,
        force_simulation: bool,
        serial_client_factory: Callable[
            [str, int, float, float],
            object,
        ] = default_serial_client_factory,
    ) -> None:
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.command_log_file = command_log_file
        self.serial_timeout = serial_timeout
        self.serial_reset_delay = serial_reset_delay
        self.force_simulation = force_simulation
        self.serial_client_factory = serial_client_factory
        self.demo_enabled = False
        self._serial_client: Optional[object] = None
        self._serial_status = "SIMULATION_MODE" if force_simulation else "NOT_CONNECTED"
        self._emergency_stop = False
        self._lock = threading.Lock()
        self._last_status = {
            "demo_enabled": False,
            "last_command": "STOP",
            "last_command_sent": "STOP",
            "requested_command": "DEFAULT",
            "command_timestamp": "",
            "serial_status": self._serial_status,
            "serial_connection_status": self._serial_status,
            "simulation_mode": self._serial_status == "SIMULATION_MODE",
            "success": True,
            "result": "DEFAULT_CLOSED",
            "message": "Default STOP / closed; Demo Mode is disabled.",
            "emergency_stop": False,
            "log_path": str(self.command_log_file),
        }

    def status(self) -> dict:
        with self._lock:
            status = dict(self._last_status)
            status["demo_enabled"] = self.demo_enabled
            status["serial_status"] = self._serial_status
            status["serial_connection_status"] = self._serial_status
            status["simulation_mode"] = self._serial_status == "SIMULATION_MODE"
            status["success"] = self._result_successful(str(status.get("result", "")))
            status["emergency_stop"] = self._emergency_stop
            status["last_command_sent"] = status.get(
                "last_command",
                status.get("last_command_sent", "STOP"),
            )
            status["log_path"] = str(self.command_log_file)
            return status

    def set_enabled(self, enabled: bool) -> tuple[dict, int]:
        with self._lock:
            if enabled:
                self.demo_enabled = True
                self._emergency_stop = False
                result, message, http_status = self._send_serial_command("STOP")
                if http_status >= 400:
                    self.demo_enabled = False
                mode_message = (
                    "Demo Mode enabled"
                    if self.demo_enabled
                    else "Demo Mode enable failed"
                )
                status = self._record_status(
                    command="STOP",
                    serial_command="STOP",
                    result=result,
                    message=f"{mode_message}; {message}",
                )
                return status, http_status

        return self.run_command("STOP", requested_command="DISABLE_DEMO", force=True)

    def run_command(
        self,
        raw_command: object,
        *,
        requested_command: Optional[str] = None,
        force: bool = False,
    ) -> tuple[dict, int]:
        normalized_command, serial_command = normalize_demo_command(raw_command)
        command_for_log = requested_command or str(raw_command or "").strip().upper()

        with self._lock:
            if normalized_command is None or serial_command is None:
                status = self._record_status(
                    command=command_for_log or "UNKNOWN",
                    serial_command="",
                    result="ERROR",
                    message="Invalid demo command.",
                )
                return status, 400

            if (
                normalized_command in DEMO_COMMANDS_REQUIRING_ENABLE
                and not self.demo_enabled
                and not force
            ):
                status = self._record_status(
                    command=normalized_command,
                    serial_command="",
                    result="BLOCKED",
                    message="Demo Mode is disabled; command was not sent.",
                )
                return status, 403

            if normalized_command == "EMERGENCY_STOP":
                self.demo_enabled = False
                self._emergency_stop = True
            else:
                self._emergency_stop = False

            if requested_command == "DISABLE_DEMO":
                self.demo_enabled = False
                self._emergency_stop = False

            result, message, http_status = self._send_serial_command(serial_command)
            status = self._record_status(
                command=command_for_log or normalized_command,
                serial_command=serial_command,
                result=result,
                message=message,
            )
            return status, http_status

    def _send_serial_command(self, serial_command: str) -> tuple[str, str, int]:
        if self.force_simulation or not self.serial_port:
            self._serial_status = "SIMULATION_MODE"
            return (
                "SIMULATED",
                f"Simulation mode: {serial_command} recorded; no hardware command sent.",
                200,
            )

        try:
            serial_client = self._ensure_serial_client()
            payload = f"{serial_command}\n".encode("utf-8")
            bytes_written = serial_client.write(payload)
            serial_client.flush()
            if isinstance(bytes_written, int) and bytes_written != len(payload):
                raise TimeoutError(
                    f"serial write incomplete: {bytes_written} of {len(payload)} bytes"
                )
            self._serial_status = "CONNECTED"
            return (
                "SENT",
                f"Sent {serial_command} to Arduino on {self.serial_port}.",
                200,
            )
        except ImportError:
            self._serial_status = "SIMULATION_MODE"
            return (
                "SIMULATED",
                "pyserial is not installed; command recorded in simulation mode.",
                200,
            )
        except TimeoutError as exc:
            self._close_serial_client()
            self._serial_status = "ERROR"
            return ("ERROR", f"Serial command timeout: {exc}", 504)
        except Exception as exc:
            self._close_serial_client()
            if "Timeout" in type(exc).__name__:
                self._serial_status = "ERROR"
                return ("ERROR", f"Serial command timeout: {exc}", 504)

            self._serial_status = "SIMULATION_MODE"
            return (
                "SIMULATED",
                f"Arduino serial unavailable; command recorded in simulation mode: {exc}",
                200,
            )

    def _ensure_serial_client(self):
        if self._serial_client is not None:
            return self._serial_client

        serial_client = self.serial_client_factory(
            self.serial_port,
            self.baudrate,
            self.serial_timeout,
            self.serial_timeout,
        )
        self._serial_client = serial_client
        self._serial_status = "CONNECTED"
        if self.serial_reset_delay > 0:
            time.sleep(self.serial_reset_delay)
        return serial_client

    def _close_serial_client(self) -> None:
        if self._serial_client is None:
            return

        try:
            self._serial_client.close()
        except Exception:
            pass
        self._serial_client = None

    def _record_status(
        self,
        *,
        command: str,
        serial_command: str,
        result: str,
        message: str,
    ) -> dict:
        timestamp = now_jst_iso()
        status = {
            "demo_enabled": self.demo_enabled,
            "last_command": serial_command or command,
            "last_command_sent": serial_command or command,
            "requested_command": command,
            "command_timestamp": timestamp,
            "serial_status": self._serial_status,
            "serial_connection_status": self._serial_status,
            "simulation_mode": self._serial_status == "SIMULATION_MODE",
            "success": self._result_successful(result),
            "result": result,
            "message": message,
            "emergency_stop": self._emergency_stop,
            "log_path": str(self.command_log_file),
        }
        self._last_status = status
        self._append_log_row(status, command, serial_command)
        return dict(status)

    def _append_log_row(self, status: dict, command: str, serial_command: str) -> None:
        self.command_log_file.parent.mkdir(parents=True, exist_ok=True)
        should_write_header = (
            not self.command_log_file.exists()
            or self.command_log_file.stat().st_size == 0
        )
        with self.command_log_file.open("a", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=DEMO_COMMAND_FIELDNAMES)
            if should_write_header:
                writer.writeheader()
            writer.writerow(
                {
                    "timestamp": status["command_timestamp"],
                    "command": command,
                    "serial_command": serial_command,
                    "demo_enabled": status["demo_enabled"],
                    "serial_status": status["serial_status"],
                    "result": status["result"],
                    "message": status["message"],
                    "emergency_stop": status["emergency_stop"],
                }
            )

    @staticmethod
    def _result_successful(result: str) -> bool:
        return result in {"DEFAULT_CLOSED", "READY", "SENT", "SIMULATED"}


def should_return_json() -> bool:
    if request.is_json:
        return True
    return (
        request.accept_mimetypes["application/json"]
        >= request.accept_mimetypes["text/html"]
    )


def demo_command_from_request() -> object:
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        if truthy(payload.get("emergency_stop")):
            return "EMERGENCY_STOP"
        return payload.get("command", "")
    return request.form.get("command", "")


def create_app(
    log_dir: Path,
    log_file: str,
    refresh_interval: int,
    *,
    camera_log_file: str,
    debug_frame_dir: Path,
    camera_frame_file: str,
    demo_serial_port: str = "/dev/ttyACM0",
    demo_baudrate: int = 115200,
    demo_command_log_file: str = "data/logs/demo_commands.csv",
    demo_log_file: Optional[str] = None,
    demo_serial_timeout: float = 1.0,
    demo_serial_reset_delay: float = 2.0,
    demo_force_simulation: bool = False,
    motor_driver_config_file: str = "config.motor_driver.json",
    serial_client_factory: Callable[
        [str, int, float, float],
        object,
    ] = default_serial_client_factory,
) -> Flask:
    app = Flask(__name__)
    app.jinja_env.globals["status_pill"] = status_pill
    app.jinja_env.globals["truthy"] = truthy
    log_dir = log_dir.resolve()
    debug_frame_dir = debug_frame_dir.resolve()
    resolved_log_file = str(Path(log_file).resolve()) if log_file else ""
    resolved_camera_log_file = str(Path(camera_log_file).resolve())
    resolved_demo_command_log_file = demo_log_file or demo_command_log_file
    demo_service = DemoCommandService(
        serial_port=demo_serial_port,
        baudrate=demo_baudrate,
        command_log_file=Path(resolved_demo_command_log_file).resolve(),
        serial_timeout=demo_serial_timeout,
        serial_reset_delay=demo_serial_reset_delay,
        force_simulation=demo_force_simulation,
        serial_client_factory=serial_client_factory,
    )
    motor_controller = MotorDriverController(Path(motor_driver_config_file))

    @app.route("/")
    def index():
        chosen_camera_log = Path(resolved_camera_log_file)
        chosen_log = (
            Path(resolved_log_file)
            if resolved_log_file
            else find_latest_log_file(
                log_dir,
                excluded_names={
                    chosen_camera_log.name,
                    demo_service.command_log_file.name,
                },
            )
        )
        row = load_latest_row(chosen_log) if chosen_log else None
        camera_row = load_latest_row(chosen_camera_log) if chosen_camera_log else None
        camera_frame_path = debug_frame_dir / camera_frame_file
        motor_status = motor_controller.get_status()
        motor_config = motor_controller.config.to_dict()
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
            demo_status=demo_service.status(),
            motor_status=motor_status.to_dict(),
            motor_config=motor_config,
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

    @app.route("/api/demo-status")
    @app.route("/api/demo/status")
    def demo_status():
        return jsonify(demo_service.status())

    @app.route("/api/demo-enable", methods=["POST"])
    @app.route("/api/demo-mode", methods=["POST"])
    def demo_mode():
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            enabled = truthy(payload.get("enabled"))
        else:
            enabled = truthy(request.form.get("enabled"))

        status, http_status = demo_service.set_enabled(enabled)
        if should_return_json():
            return jsonify(status), http_status
        return redirect(url_for("index"), code=303)

    @app.route("/api/demo-command", methods=["POST"])
    def demo_command():
        command = demo_command_from_request()
        status, http_status = demo_service.run_command(command)
        if should_return_json():
            return jsonify(status), http_status
        return redirect(url_for("index"), code=303)

    @app.route("/api/demo/release", methods=["POST"])
    def demo_release():
        status, http_status = demo_service.run_command("RELEASE")
        if should_return_json():
            return jsonify(status), http_status
        return redirect(url_for("index"), code=303)

    @app.route("/api/demo/stop", methods=["POST"])
    def demo_stop():
        status, http_status = demo_service.run_command("STOP")
        if should_return_json():
            return jsonify(status), http_status
        return redirect(url_for("index"), code=303)

    @app.route("/api/demo/test", methods=["POST"])
    def demo_test():
        status, http_status = demo_service.run_command("TEST")
        if should_return_json():
            return jsonify(status), http_status
        return redirect(url_for("index"), code=303)

    @app.route("/api/demo/emergency-stop", methods=["POST"])
    def demo_emergency_stop():
        status, http_status = demo_service.run_command("EMERGENCY_STOP")
        if should_return_json():
            return jsonify(status), http_status
        return redirect(url_for("index"), code=303)

    @app.route("/api/motor/status")
    def motor_status():
        status = motor_controller.get_status()
        return jsonify(status.to_dict())

    @app.route("/api/motor/config", methods=["GET"])
    def motor_config_get():
        return jsonify(motor_controller.config.to_dict())

    @app.route("/api/motor/config", methods=["POST"])
    @app.route("/motor/config", methods=["POST"])
    def motor_config():
        if request.is_json:
            payload = request.get_json(silent=True) or {}
        else:
            payload = {}
            for key in request.form:
                value = request.form[key]
                if value.lower() == "true":
                    payload[key] = True
                elif value.lower() == "false":
                    payload[key] = False
                else:
                    try:
                        payload[key] = int(value)
                    except ValueError:
                        payload[key] = value
        motor_controller.update_config(payload)
        if should_return_json():
            return jsonify(motor_controller.config.to_dict())
        return redirect(url_for("index"), code=303)

    @app.route("/motor/open", methods=["POST"])
    @app.route("/api/motor/open", methods=["POST"])
    def motor_open():
        success, message = motor_controller.open_motor()
        if should_return_json():
            return jsonify({"success": success, "message": message}), 200 if success else 500
        return redirect(url_for("index"), code=303)

    @app.route("/motor/close", methods=["POST"])
    @app.route("/api/motor/close", methods=["POST"])
    def motor_close():
        success, message = motor_controller.close_motor()
        if should_return_json():
            return jsonify({"success": success, "message": message}), 200 if success else 500
        return redirect(url_for("index"), code=303)

    @app.route("/motor/test", methods=["POST"])
    @app.route("/api/motor/test", methods=["POST"])
    def motor_test():
        success, message = motor_controller.test_connection()
        if should_return_json():
            return jsonify({"success": success, "message": message}), 200 if success else 500
        return redirect(url_for("index"), code=303)

    @app.route("/motor/emergency-stop", methods=["POST"])
    @app.route("/api/motor/emergency-stop", methods=["POST"])
    def motor_emergency_stop():
        success, message = motor_controller.emergency_stop()
        if should_return_json():
            return jsonify({"success": success, "message": message}), 200 if success else 500
        return redirect(url_for("index"), code=303)

    @app.route("/motor/reset", methods=["POST"])
    @app.route("/api/motor/reset", methods=["POST"])
    def motor_reset():
        success, message = motor_controller.reset()
        if should_return_json():
            return jsonify({"success": success, "message": message}), 200 if success else 500
        return redirect(url_for("index"), code=303)

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
        demo_serial_port=args.demo_serial_port,
        demo_baudrate=args.demo_baudrate,
        demo_command_log_file=args.demo_command_log_file,
        demo_serial_timeout=args.demo_serial_timeout,
        demo_serial_reset_delay=args.demo_serial_reset_delay,
        demo_force_simulation=args.demo_force_simulation,
        motor_driver_config_file=args.motor_driver_config,
    )
    app.run(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
