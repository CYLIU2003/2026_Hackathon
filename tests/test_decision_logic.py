HONEY_MIN_THRESHOLD_PERCENT = 20


def decide_release_state(
    bear_detected: bool,
    paw_contact: bool,
    honey_amount_percent: int,
    system_safe: bool,
    emergency_stop: bool,
) -> str:
    if honey_amount_percent < 0 or honey_amount_percent > 100:
        return "RELEASE_OFF"

    if (
        bear_detected
        and paw_contact
        and honey_amount_percent >= HONEY_MIN_THRESHOLD_PERCENT
        and system_safe
        and not emergency_stop
    ):
        return "RELEASE_ON"
    return "RELEASE_OFF"


def test_no_bear():
    assert decide_release_state(False, False, 80, True, False) == "RELEASE_OFF"


def test_bear_no_contact():
    assert decide_release_state(True, False, 80, True, False) == "RELEASE_OFF"


def test_contact_honey_low():
    assert decide_release_state(True, True, 10, True, False) == "RELEASE_OFF"


def test_ready_to_release():
    assert decide_release_state(True, True, 80, True, False) == "RELEASE_ON"


def test_unsafe_system():
    assert decide_release_state(True, True, 80, False, False) == "RELEASE_OFF"


def test_emergency_stop():
    assert decide_release_state(True, True, 80, True, True) == "RELEASE_OFF"


def test_invalid_honey_amount():
    assert decide_release_state(True, True, 200, True, False) == "RELEASE_OFF"
