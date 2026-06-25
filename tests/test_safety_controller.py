from pathlib import Path

from raspberry_pi.safety_control.safety_controller import (
    CameraCsvInput,
    SafetyConfig,
    SafetyStateMachine,
    SensorSnapshot,
)


CONFIG_PATH = (
    Path(__file__).parents[1]
    / "raspberry_pi/safety_control/config.safety_control.json"
)


def snapshot(**overrides) -> SensorSnapshot:
    values = {
        "bear_detected": False,
        "confidence": None,
        "bear_box_area_ratio": None,
        "contact_detected": False,
        "impedance_kohm": None,
        "honey_amount_percent": 80,
        "system_safe": True,
        "emergency_stop": False,
    }
    values.update(overrides)
    return SensorSnapshot(**values)


def test_release_requires_bear_confirmed_contact_honey_and_safety():
    machine = SafetyStateMachine(SafetyConfig.load(CONFIG_PATH))

    assert machine.update(snapshot(), 0)["release_state"] == "RELEASE_OFF"
    machine.update(snapshot(bear_detected=True), 100)
    machine.update(
        snapshot(bear_detected=True, contact_detected=True),
        200,
    )
    contact = machine.update(
        snapshot(bear_detected=True, contact_detected=True),
        700,
    )
    ready = machine.update(
        snapshot(bear_detected=True, contact_detected=True),
        800,
    )
    releasing = machine.update(
        snapshot(bear_detected=True, contact_detected=True),
        900,
    )

    assert contact["state"] == "CONTACT_CONFIRMED"
    assert ready["state"] == "READY_TO_RELEASE"
    assert releasing["state"] == "RELEASING"
    assert releasing["safety_decision"] == "SAFE_TO_FEED"
    assert releasing["servo_command"] == "RELEASE"


def test_release_times_out_and_enters_cooldown():
    config = SafetyConfig.load(CONFIG_PATH)
    machine = SafetyStateMachine(config)
    safe = snapshot(bear_detected=True, contact_detected=True)
    machine.update(safe, 0)
    machine.update(safe, config.contact_confirm_duration_ms)
    machine.update(safe, 600)
    machine.update(safe, 700)

    decision = machine.update(
        safe,
        700 + config.max_release_duration_ms,
    )

    assert decision["state"] == "COOLDOWN"
    assert decision["release_state"] == "RELEASE_OFF"
    assert decision["servo_command"] == "HOLD"


def test_invalid_input_and_emergency_stop_are_fail_safe():
    config = SafetyConfig.load(CONFIG_PATH)

    invalid = SafetyStateMachine(config).update(
        snapshot(bear_detected=True, contact_detected=True, honey_amount_percent=101),
        0,
    )
    emergency = SafetyStateMachine(config).update(
        snapshot(bear_detected=True, contact_detected=True, emergency_stop=True),
        0,
    )

    assert invalid["state"] == "ERROR_SAFE"
    assert invalid["release_state"] == "RELEASE_OFF"
    assert emergency["state"] == "ERROR_SAFE"
    assert emergency["release_state"] == "RELEASE_OFF"


def test_missing_camera_data_is_fail_safe():
    machine = SafetyStateMachine(SafetyConfig.load(CONFIG_PATH))

    decision = machine.update(
        snapshot(source_ok=False, source_error="camera data timed out"),
        0,
    )

    assert decision["state"] == "ERROR_SAFE"
    assert decision["safety_decision"] == "ERROR_SAFE"
    assert decision["servo_command"] == "HOLD"


def test_detected_bear_waits_for_approach_confirmation():
    machine = SafetyStateMachine(SafetyConfig.load(CONFIG_PATH))

    decision = machine.update(
        snapshot(
            bear_detected=True,
            bear_approaching=False,
            contact_detected=True,
        ),
        1000,
    )

    assert decision["state"] == "BEAR_DETECTED"
    assert decision["safety_decision"] == "WAIT_APPROACH"
    assert decision["servo_command"] == "HOLD"


def test_camera_input_requests_reset_once_after_data_recovers(tmp_path):
    config = SafetyConfig.load(CONFIG_PATH)
    camera_log = tmp_path / "camera_ai_log.csv"
    source = CameraCsvInput(
        camera_log,
        config,
        mock_contact=True,
        mock_impedance_kohm=92.4,
        honey_amount_percent=80,
        system_safe=True,
        emergency_stop=False,
    )

    missing = source.read()
    camera_log.write_text(
        "ai_camera_ok,ai_model_ok,ai_bear_detected,"
        "ai_bear_approaching,ai_bear_confidence,"
        "ai_bear_box_area_ratio\n"
        "true,true,true,true,0.86,0.18\n",
        encoding="utf-8",
    )
    recovered = source.read()
    next_read = source.read()

    assert missing.source_ok is False
    assert recovered.reset_requested is True
    assert recovered.bear_detected is True
    assert recovered.bear_approaching is True
    assert next_read.reset_requested is False
