/*
  A1 Front Paw Contact Pad System
  Standalone Goda PCA9685 Servo Actuator + Contact Pad Controller

  Purpose:
    - Keep the existing safety state machine.
    - Use Goda-san's PCA9685 + servo code only as the actuator layer.
    - Drive the honey release servo only while state == RELEASING.
    - Provide test modes for cases where Raspberry Pi is unavailable.

  このファイルは standalone 参照用です。
  メインのスケッチは contact_pad_controller/contact_pad_controller.ino です。

  Arduino IDE で開くときは actuator_standalone フォルダごと開いてください。

  Required Arduino IDE library:
    - Adafruit PWM Servo Driver Library
*/

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// -----------------------------------------------------------------------------
// 設定値（config.h の代わり。このファイル単体で完結します）
// メインスケッチでは config.h を使います。
// -----------------------------------------------------------------------------
const int PIN_RELEASE_LED = 13;
const int PIN_RELEASE_SIGNAL = 8;
const int PIN_STATUS_LED = 12;
const int HONEY_MIN_THRESHOLD_PERCENT = 20;
const unsigned long CONTACT_CONFIRM_DURATION_MS = 500;
const unsigned long MAX_RELEASE_DURATION_MS = 3000;
const unsigned long COOLDOWN_AFTER_RELEASE_MS = 5000;
const unsigned long MESSAGE_INTERVAL_MS = 1000;
const unsigned long SENSOR_UPDATE_INTERVAL_MS = 100;
const int SERIAL_BAUDRATE = 115200;
const int DEFAULT_HONEY_AMOUNT_PERCENT = 80;

// -----------------------------------------------------------------------------
// Goda actuator settings: PCA9685 + servo motor
// -----------------------------------------------------------------------------
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

const uint8_t SERVO_CHANNEL = 0;
const int SERVO_MIN_PULSE = 150;  // 0 deg approximate count at 50 Hz
const int SERVO_MAX_PULSE = 500;  // 180 deg approximate count at 50 Hz
const int SERVO_CLOSED_ANGLE = 0;
const int SERVO_OPEN_ANGLE = 90;  // Start safely. Tune after mechanical check.
const int SERVO_STEP_DEG = 5;
const int SERVO_STEP_DELAY_MS = 15;
const unsigned long ACTUATOR_REFRESH_INTERVAL_MS = 250;

int current_servo_angle = SERVO_CLOSED_ANGLE;
bool actuator_open = false;
unsigned long last_actuator_refresh_ms = 0;

int angleToPulse(int angle) {
  angle = constrain(angle, 0, 180);
  return map(angle, 0, 180, SERVO_MIN_PULSE, SERVO_MAX_PULSE);
}

void writeServoAngle(int angle) {
  angle = constrain(angle, 0, 180);
  pwm.setPWM(SERVO_CHANNEL, 0, angleToPulse(angle));
  current_servo_angle = angle;
}

void moveServoSmooth(int targetAngle) {
  targetAngle = constrain(targetAngle, 0, 180);
  if (targetAngle == current_servo_angle) {
    writeServoAngle(targetAngle);
    return;
  }

  int direction = (targetAngle > current_servo_angle) ? 1 : -1;
  int angle = current_servo_angle;

  while (angle != targetAngle) {
    angle += direction * SERVO_STEP_DEG;
    if ((direction > 0 && angle > targetAngle) || (direction < 0 && angle < targetAngle)) {
      angle = targetAngle;
    }
    writeServoAngle(angle);
    delay(SERVO_STEP_DELAY_MS);
  }
}

void closeReleaseGate() {
  if (actuator_open || current_servo_angle != SERVO_CLOSED_ANGLE) {
    moveServoSmooth(SERVO_CLOSED_ANGLE);
  }
  actuator_open = false;
}

void openReleaseGate() {
  if (!actuator_open || current_servo_angle != SERVO_OPEN_ANGLE) {
    moveServoSmooth(SERVO_OPEN_ANGLE);
  }
  actuator_open = true;
}

void initReleaseActuator() {
  Wire.begin();
  pwm.begin();
  pwm.setOscillatorFrequency(27000000);
  pwm.setPWMFreq(50);
  delay(10);
  writeServoAngle(SERVO_CLOSED_ANGLE);
  actuator_open = false;
}

// -----------------------------------------------------------------------------
// State machine
// -----------------------------------------------------------------------------
enum State {
  IDLE,
  BEAR_DETECTED,
  CONTACT_CONFIRMED,
  READY_TO_RELEASE,
  RELEASING,
  COOLDOWN,
  ERROR_SAFE
};

State state = IDLE;
State previous_state = IDLE;

const char *event_name = "BOOT";
const char *release_state = "RELEASE_OFF";
const char *error_code = "ERR_NONE";
const char *error_message = NULL;

// Inputs. These can be driven by internal test mode or serial commands.
bool simulated_bear_detected = false;
bool simulated_paw_contact = false;
int simulated_honey_amount_percent = DEFAULT_HONEY_AMOUNT_PERCENT;
bool simulated_system_safe = true;
bool emergency_stop = false;

bool bear_detected = false;
bool paw_contact = false;
int honey_amount_percent = DEFAULT_HONEY_AMOUNT_PERCENT;
bool system_safe = true;

bool contact_confirmed = false;
bool honey_enough = true;
bool release_allowed = false;
bool reset_requested = false;
bool demo_command_active = false;

// Test mode. ON by default so Arduino alone can demonstrate the sequence.
bool auto_test_mode = true;
int simulation_step = 0;
unsigned long simulation_step_started_at_ms = 0;
const unsigned long SIMULATION_STEP_DURATION_MS = 5000;

unsigned long current_time_ms = 0;
unsigned long state_entered_at_ms = 0;
unsigned long last_contact_time_ms = 0;
unsigned long release_started_at_ms = 0;
unsigned long cooldown_started_at_ms = 0;
unsigned long last_message_sent_at_ms = 0;
unsigned long last_sensor_update_at_ms = 0;

char serial_command_buffer[80];
int serial_command_length = 0;

const char *state_to_string(State value) {
  switch (value) {
    case IDLE: return "IDLE";
    case BEAR_DETECTED: return "BEAR_DETECTED";
    case CONTACT_CONFIRMED: return "CONTACT_CONFIRMED";
    case READY_TO_RELEASE: return "READY_TO_RELEASE";
    case RELEASING: return "RELEASING";
    case COOLDOWN: return "COOLDOWN";
    case ERROR_SAFE: return "ERROR_SAFE";
    default: return "ERROR_SAFE";
  }
}

void set_error(const char *code, const char *message) {
  error_code = code;
  error_message = message;
}

void clear_error() {
  error_code = "ERR_NONE";
  error_message = NULL;
}

void request_reset() {
  reset_requested = true;
}

void clear_serial_command_buffer() {
  serial_command_length = 0;
  serial_command_buffer[0] = '\0';
}

void enter_state(State next_state, const char *next_event) {
  if (state == next_state) {
    return;
  }

  previous_state = state;
  state = next_state;
  event_name = next_event;
  state_entered_at_ms = current_time_ms;

  if (state == RELEASING) {
    release_started_at_ms = current_time_ms;
  }
  if (state == COOLDOWN) {
    cooldown_started_at_ms = current_time_ms;
  }
}

void set_manual_input(const char *key, int value) {
  auto_test_mode = false;
  demo_command_active = false;

  if (strcmp(key, "AI_BEAR") == 0 || strcmp(key, "BEAR") == 0) {
    simulated_bear_detected = value != 0;
    event_name = simulated_bear_detected ? "SERIAL_AI_BEAR_ON" : "SERIAL_AI_BEAR_OFF";
  } else if (strcmp(key, "PAW") == 0 || strcmp(key, "CONTACT") == 0) {
    simulated_paw_contact = value != 0;
    event_name = simulated_paw_contact ? "SERIAL_PAW_ON" : "SERIAL_PAW_OFF";
  } else if (strcmp(key, "HONEY") == 0) {
    simulated_honey_amount_percent = value;
    event_name = "SERIAL_HONEY_SET";
  } else if (strcmp(key, "SAFE") == 0) {
    simulated_system_safe = value != 0;
    event_name = simulated_system_safe ? "SERIAL_SAFE_ON" : "SERIAL_SAFE_OFF";
  } else if (strcmp(key, "ESTOP") == 0 || strcmp(key, "EMERGENCY") == 0) {
    emergency_stop = value != 0;
    event_name = emergency_stop ? "SERIAL_ESTOP_ON" : "SERIAL_ESTOP_OFF";
  } else {
    set_error("ERR_UNKNOWN_COMMAND", "unknown SET key");
    enter_state(ERROR_SAFE, "UNKNOWN_SERIAL_COMMAND");
  }
}

void request_demo_release(const char *next_event) {
  auto_test_mode = false;

  if (state == ERROR_SAFE) {
    demo_command_active = false;
    event_name = "DEMO_RELEASE_BLOCKED_ERROR_SAFE";
    return;
  }

  demo_command_active = true;
  emergency_stop = false;
  simulated_bear_detected = true;
  simulated_paw_contact = true;
  simulated_honey_amount_percent = DEFAULT_HONEY_AMOUNT_PERCENT;
  if (simulated_honey_amount_percent < HONEY_MIN_THRESHOLD_PERCENT) {
    simulated_honey_amount_percent = HONEY_MIN_THRESHOLD_PERCENT;
  }
  simulated_system_safe = true;
  last_contact_time_ms = 0;
  contact_confirmed = false;
  event_name = next_event;
}

void stop_demo_release(const char *next_event) {
  auto_test_mode = false;
  demo_command_active = false;
  simulated_bear_detected = false;
  simulated_paw_contact = false;
  simulated_honey_amount_percent = DEFAULT_HONEY_AMOUNT_PERCENT;
  simulated_system_safe = true;
  emergency_stop = false;
  contact_confirmed = false;
  last_contact_time_ms = 0;
  event_name = next_event;
  closeReleaseGate();

  if (state == RELEASING) {
    enter_state(COOLDOWN, next_event);
  } else if (state != ERROR_SAFE) {
    enter_state(IDLE, next_event);
  }
}

void handle_serial_command(char *command) {
  // Trim leading spaces.
  while (*command == ' ') {
    command++;
  }

  if (strcmp(command, "RELEASE") == 0) {
    request_demo_release("DEMO_RELEASE_COMMAND");
    return;
  }

  if (strcmp(command, "STOP") == 0) {
    stop_demo_release("DEMO_STOP_COMMAND");
    return;
  }

  if (strcmp(command, "TEST") == 0) {
    request_demo_release("DEMO_TEST_COMMAND");
    return;
  }

  if (strcmp(command, "RESET") == 0) {
    request_reset();
    emergency_stop = false;
    event_name = "RESET_REQUEST";
    return;
  }

  if (strcmp(command, "STATUS") == 0) {
    event_name = "STATUS_REQUEST";
    return;
  }

  if (strcmp(command, "TEST_AUTO_ON") == 0) {
    auto_test_mode = true;
    demo_command_active = false;
    simulation_step = 0;
    simulation_step_started_at_ms = current_time_ms;
    event_name = "TEST_AUTO_ON";
    return;
  }

  if (strcmp(command, "TEST_AUTO_OFF") == 0) {
    auto_test_mode = false;
    demo_command_active = false;
    simulated_bear_detected = false;
    simulated_paw_contact = false;
    simulated_honey_amount_percent = DEFAULT_HONEY_AMOUNT_PERCENT;
    simulated_system_safe = true;
    emergency_stop = false;
    event_name = "TEST_AUTO_OFF";
    return;
  }

  if (strncmp(command, "SET ", 4) == 0) {
    char key[24];
    int value = 0;
    int parsed = sscanf(command + 4, "%23s %d", key, &value);
    if (parsed == 2) {
      set_manual_input(key, value);
      return;
    }
    set_error("ERR_BAD_SET_COMMAND", "expected: SET KEY VALUE");
    enter_state(ERROR_SAFE, "BAD_SERIAL_COMMAND");
    return;
  }

  set_error("ERR_UNKNOWN_COMMAND", "unknown serial command");
  enter_state(ERROR_SAFE, "UNKNOWN_SERIAL_COMMAND");
}

void process_serial_commands() {
  while (Serial.available() > 0) {
    char incoming = static_cast<char>(Serial.read());

    if (incoming == '\r') {
      continue;
    }

    if (incoming == '\n') {
      if (serial_command_length > 0) {
        serial_command_buffer[serial_command_length] = '\0';
        handle_serial_command(serial_command_buffer);
        clear_serial_command_buffer();
      }
      continue;
    }

    if (serial_command_length < static_cast<int>(sizeof(serial_command_buffer)) - 1) {
      serial_command_buffer[serial_command_length++] = incoming;
    }
  }
}

void update_simulation_inputs() {
  if (!auto_test_mode) {
    return;
  }

  if (current_time_ms - simulation_step_started_at_ms >= SIMULATION_STEP_DURATION_MS) {
    simulation_step = (simulation_step + 1) % 6;
    simulation_step_started_at_ms = current_time_ms;
  }

  switch (simulation_step) {
    case 0:
      simulated_bear_detected = false;
      simulated_paw_contact = false;
      simulated_honey_amount_percent = 80;
      simulated_system_safe = true;
      emergency_stop = false;
      break;
    case 1:
      simulated_bear_detected = true;
      simulated_paw_contact = false;
      simulated_honey_amount_percent = 80;
      simulated_system_safe = true;
      emergency_stop = false;
      break;
    case 2:
      simulated_bear_detected = true;
      simulated_paw_contact = true;
      simulated_honey_amount_percent = 80;
      simulated_system_safe = true;
      emergency_stop = false;
      break;
    case 3:
      simulated_bear_detected = true;
      simulated_paw_contact = true;
      simulated_honey_amount_percent = 10;
      simulated_system_safe = true;
      emergency_stop = false;
      break;
    case 4:
      simulated_bear_detected = true;
      simulated_paw_contact = true;
      simulated_honey_amount_percent = 80;
      simulated_system_safe = false;
      emergency_stop = false;
      break;
    case 5:
      simulated_bear_detected = true;
      simulated_paw_contact = true;
      simulated_honey_amount_percent = 80;
      simulated_system_safe = true;
      emergency_stop = true;
      break;
    default:
      break;
  }
}

bool inputs_valid() {
  if (honey_amount_percent < 0 || honey_amount_percent > 100) {
    set_error("ERR_INVALID_HONEY_AMOUNT", "honey_amount_percent out of range");
    return false;
  }
  return true;
}

void update_confirmed_contact() {
  if (paw_contact) {
    if (last_contact_time_ms == 0) {
      last_contact_time_ms = current_time_ms;
    }
    if (current_time_ms - last_contact_time_ms >= CONTACT_CONFIRM_DURATION_MS) {
      contact_confirmed = true;
    }
  } else {
    last_contact_time_ms = 0;
    contact_confirmed = false;
  }
}

void update_inputs() {
  bear_detected = simulated_bear_detected;
  paw_contact = simulated_paw_contact;
  honey_amount_percent = simulated_honey_amount_percent;
  system_safe = simulated_system_safe;

  update_confirmed_contact();
  honey_enough = honey_amount_percent >= HONEY_MIN_THRESHOLD_PERCENT;
  release_allowed = bear_detected && contact_confirmed && honey_enough && system_safe && !emergency_stop;
}

void process_state_machine() {
  if (state != ERROR_SAFE) {
    reset_requested = false;
  }

  if (emergency_stop) {
    demo_command_active = false;
    closeReleaseGate();
    set_error("ERR_EMERGENCY_STOP", "emergency_stop active");
    enter_state(ERROR_SAFE, "EMERGENCY_STOP");
    return;
  }

  if (!inputs_valid()) {
    demo_command_active = false;
    closeReleaseGate();
    enter_state(ERROR_SAFE, "INVALID_INPUT");
    return;
  }

  if (state == ERROR_SAFE) {
    closeReleaseGate();
    if (reset_requested && inputs_valid() && !emergency_stop) {
      clear_error();
      reset_requested = false;
      enter_state(IDLE, "RESET");
    }
    return;
  }

  switch (state) {
    case IDLE:
      if (bear_detected) {
        enter_state(BEAR_DETECTED, "BEAR_DETECTED");
      }
      break;

    case BEAR_DETECTED:
      if (!bear_detected) {
        enter_state(IDLE, "IDLE");
      } else if (contact_confirmed) {
        enter_state(CONTACT_CONFIRMED, "CONTACT_CONFIRMED");
      }
      break;

    case CONTACT_CONFIRMED:
      if (!bear_detected) {
        enter_state(IDLE, "IDLE");
      } else if (!paw_contact) {
        enter_state(BEAR_DETECTED, "BEAR_DETECTED");
      } else if (release_allowed) {
        enter_state(READY_TO_RELEASE, "READY_TO_RELEASE");
      } else if (!honey_enough) {
        event_name = "HONEY_LOW";
      }
      break;

    case READY_TO_RELEASE:
      if (release_allowed) {
        enter_state(RELEASING, "RELEASE_START");
      } else {
        enter_state(CONTACT_CONFIRMED, "CONTACT_CONFIRMED");
      }
      break;

    case RELEASING:
      if (!release_allowed) {
        demo_command_active = false;
        enter_state(COOLDOWN, "RELEASE_ABORTED");
      } else if (current_time_ms - release_started_at_ms >= MAX_RELEASE_DURATION_MS) {
        if (demo_command_active) {
          simulated_bear_detected = false;
          simulated_paw_contact = false;
          contact_confirmed = false;
          last_contact_time_ms = 0;
          demo_command_active = false;
        }
        enter_state(COOLDOWN, "RELEASE_TIMEOUT");
      }
      break;

    case COOLDOWN:
      if (current_time_ms - cooldown_started_at_ms >= COOLDOWN_AFTER_RELEASE_MS) {
        enter_state(IDLE, "COOLDOWN_END");
      }
      break;

    case ERROR_SAFE:
      break;

    default:
      set_error("ERR_INVALID_STATE", "unknown state");
      enter_state(ERROR_SAFE, "ERROR");
      break;
  }
}

String timestamp_string() {
  return String("T+") + String(current_time_ms) + "ms";
}

void print_bool(bool value) {
  Serial.print(value ? "true" : "false");
}

void print_nullable_string(const char *value) {
  if (value == NULL) {
    Serial.print("null");
  } else {
    Serial.print("\"");
    Serial.print(value);
    Serial.print("\"");
  }
}

void emit_json_line() {
  Serial.print("{\"timestamp\":\"");
  Serial.print(timestamp_string());
  Serial.print("\",\"state\":\"");
  Serial.print(state_to_string(state));
  Serial.print("\",\"previous_state\":\"");
  Serial.print(state_to_string(previous_state));
  Serial.print("\",\"event\":\"");
  Serial.print(event_name);
  Serial.print("\",\"bear_detected\":");
  print_bool(bear_detected);
  Serial.print(",\"paw_contact\":");
  print_bool(paw_contact);
  Serial.print(",\"contact_confirmed\":");
  print_bool(contact_confirmed);
  Serial.print(",\"raw_contact_value\":null");
  Serial.print(",\"honey_amount_percent\":");
  Serial.print(honey_amount_percent);
  Serial.print(",\"honey_enough\":");
  print_bool(honey_enough);
  Serial.print(",\"system_safe\":");
  print_bool(system_safe);
  Serial.print(",\"emergency_stop\":");
  print_bool(emergency_stop);
  Serial.print(",\"release_allowed\":");
  print_bool(release_allowed);
  Serial.print(",\"release_state\":\"");
  Serial.print(release_state);
  Serial.print("\",\"actuator_open\":");
  print_bool(actuator_open);
  Serial.print(",\"servo_angle\":");
  Serial.print(current_servo_angle);
  Serial.print(",\"auto_test_mode\":");
  print_bool(auto_test_mode);
  Serial.print(",\"error_code\":\"");
  Serial.print(error_code);
  Serial.print("\",\"error_message\":");
  print_nullable_string(error_message);
  Serial.print("}");
  Serial.println();
}

void update_outputs() {
  bool should_release = state == RELEASING;
  release_state = should_release ? "RELEASE_ON" : "RELEASE_OFF";

  digitalWrite(PIN_RELEASE_SIGNAL, should_release ? HIGH : LOW);
  digitalWrite(PIN_RELEASE_LED, should_release ? HIGH : LOW);
  digitalWrite(PIN_STATUS_LED, state == IDLE ? LOW : HIGH);

  if (current_time_ms - last_actuator_refresh_ms >= ACTUATOR_REFRESH_INTERVAL_MS) {
    last_actuator_refresh_ms = current_time_ms;
    if (should_release) {
      openReleaseGate();
    } else {
      closeReleaseGate();
    }
  }
}

void setup() {
  pinMode(PIN_RELEASE_LED, OUTPUT);
  pinMode(PIN_RELEASE_SIGNAL, OUTPUT);
  pinMode(PIN_STATUS_LED, OUTPUT);

  Serial.begin(SERIAL_BAUDRATE);
  current_time_ms = millis();
  state_entered_at_ms = current_time_ms;
  simulation_step_started_at_ms = current_time_ms;

  clear_serial_command_buffer();
  initReleaseActuator();

  update_inputs();
  update_outputs();
  emit_json_line();
}

void loop() {
  current_time_ms = millis();
  process_serial_commands();

  if (current_time_ms - last_sensor_update_at_ms >= SENSOR_UPDATE_INTERVAL_MS) {
    last_sensor_update_at_ms = current_time_ms;
    update_simulation_inputs();
    update_inputs();
  }

  process_state_machine();
  update_outputs();

  if (current_time_ms - last_message_sent_at_ms >= MESSAGE_INTERVAL_MS) {
    last_message_sent_at_ms = current_time_ms;
    emit_json_line();
  }
}
