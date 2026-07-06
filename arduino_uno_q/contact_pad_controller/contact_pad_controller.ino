#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include "config.h"

#if BIA_INPUT_ENABLED
#if BIA_USE_HARDWARE_SERIAL1
#define bia_serial Serial1
#else
#include <SoftwareSerial.h>
SoftwareSerial bia_serial(PIN_BIA_SERIAL_RX, PIN_BIA_SERIAL_TX_UNUSED);
#endif
#endif

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(GODA_PCA9685_I2C_ADDRESS);

int current_servo_angle = GODA_SERVO_CLOSED_ANGLE;
bool actuator_open = false;

enum State {
  IDLE,
  BEAR_DETECTED,
  CONTACT_CONFIRMED,
  READY_TO_RELEASE,
  RELEASING,
  COOLDOWN,
  ERROR_SAFE
};

void enter_state(State next_state, const char *next_event);

State state = IDLE;
State previous_state = IDLE;

const char *event_name = "BOOT";
const char *release_state = "RELEASE_OFF";
const char *error_code = "ERR_NONE";
const char *error_message = NULL;

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
bool auto_test_mode = true;
bool demo_command_active = false;

bool bia_data_valid = false;
bool bia_contact_detected = false;
float bia_amplitude1 = 0.0f;
float bia_phase1 = 0.0f;
float bia_amplitude2 = 0.0f;
float bia_phase2 = 0.0f;
const char *contact_input_source = "SIMULATED";

int simulation_step = 0;
unsigned long simulation_step_started_at_ms = 0;

unsigned long current_time_ms = 0;
unsigned long state_entered_at_ms = 0;
unsigned long last_contact_time_ms = 0;
unsigned long release_started_at_ms = 0;
unsigned long cooldown_started_at_ms = 0;
unsigned long last_message_sent_at_ms = 0;
unsigned long last_sensor_update_at_ms = 0;
unsigned long last_bia_message_received_at_ms = 0;

const unsigned long SIMULATION_STEP_DURATION_MS = 5000;
char serial_command_buffer[80];
int serial_command_length = 0;
char bia_message_buffer[BIA_MESSAGE_BUFFER_SIZE];
int bia_message_length = 0;

int angle_to_pulse(int angle) {
  angle = constrain(angle, 0, 180);
  return map(angle, 0, 180, GODA_SERVO_MIN_PULSE, GODA_SERVO_MAX_PULSE);
}

void write_servo_angle(int angle) {
  angle = constrain(angle, 0, 180);
  pwm.setPWM(GODA_SERVO_CHANNEL, 0, angle_to_pulse(angle));
  current_servo_angle = angle;
}

void move_servo_smooth(int target_angle) {
  target_angle = constrain(target_angle, 0, 180);
  if (target_angle == current_servo_angle) {
    write_servo_angle(target_angle);
    return;
  }

  int direction = (target_angle > current_servo_angle) ? 1 : -1;
  int angle = current_servo_angle;

  while (angle != target_angle) {
    angle += direction * GODA_SERVO_STEP_DEG;
    if ((direction > 0 && angle > target_angle) || (direction < 0 && angle < target_angle)) {
      angle = target_angle;
    }
    write_servo_angle(angle);
    delay(GODA_SERVO_STEP_DELAY_MS);
  }
}

void close_release_gate() {
  if (actuator_open || current_servo_angle != GODA_SERVO_CLOSED_ANGLE) {
    move_servo_smooth(GODA_SERVO_CLOSED_ANGLE);
  }
  actuator_open = false;
}

void open_release_gate() {
  if (!actuator_open || current_servo_angle != GODA_SERVO_OPEN_ANGLE) {
    move_servo_smooth(GODA_SERVO_OPEN_ANGLE);
  }
  actuator_open = true;
}

void init_release_actuator() {
  Wire.begin();
  pwm.begin();
  pwm.setOscillatorFrequency(27000000);
  pwm.setPWMFreq(50);
  delay(10);
  write_servo_angle(GODA_SERVO_CLOSED_ANGLE);
  actuator_open = false;
}

const char *state_to_string(State value) {
  switch (value) {
    case IDLE:
      return "IDLE";
    case BEAR_DETECTED:
      return "BEAR_DETECTED";
    case CONTACT_CONFIRMED:
      return "CONTACT_CONFIRMED";
    case READY_TO_RELEASE:
      return "READY_TO_RELEASE";
    case RELEASING:
      return "RELEASING";
    case COOLDOWN:
      return "COOLDOWN";
    case ERROR_SAFE:
      return "ERROR_SAFE";
    default:
      return "ERROR_SAFE";
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

void clear_bia_message_buffer() {
  bia_message_length = 0;
  bia_message_buffer[0] = '\0';
}

const char *find_json_value(const char *message, const char *key) {
  const char *key_position = strstr(message, key);
  if (key_position == NULL) {
    return NULL;
  }

  const char *colon_position = strchr(key_position, ':');
  if (colon_position == NULL) {
    return NULL;
  }

  const char *value_position = colon_position + 1;
  while (*value_position == ' ') {
    value_position++;
  }
  return value_position;
}

bool parse_json_bool(const char *message, const char *key, bool &value) {
  const char *value_position = find_json_value(message, key);
  if (value_position == NULL) {
    return false;
  }

  if (strncmp(value_position, "true", 4) == 0) {
    value = true;
    return true;
  }

  if (strncmp(value_position, "false", 5) == 0) {
    value = false;
    return true;
  }

  return false;
}

bool parse_json_float(const char *message, const char *key, float &value) {
  const char *value_position = find_json_value(message, key);
  if (value_position == NULL) {
    return false;
  }

  char *end_position = NULL;
  double parsed_value = strtod(value_position, &end_position);
  if (end_position == value_position) {
    return false;
  }

  value = static_cast<float>(parsed_value);
  return true;
}

bool parse_bia_message(const char *message) {
  bool next_contact_detected = false;
  float next_amplitude1 = 0.0f;
  float next_phase1 = 0.0f;
  float next_amplitude2 = 0.0f;
  float next_phase2 = 0.0f;

  if (!parse_json_bool(message, "\"contact_detected\"", next_contact_detected)) {
    return false;
  }

  if (!parse_json_float(message, "\"amplitude1\"", next_amplitude1)) {
    return false;
  }

  parse_json_float(message, "\"phase1\"", next_phase1);
  parse_json_float(message, "\"amplitude2\"", next_amplitude2);
  parse_json_float(message, "\"phase2\"", next_phase2);

  if (next_amplitude1 < 0.0f) {
    return false;
  }

  bia_contact_detected = next_contact_detected;
  bia_amplitude1 = next_amplitude1;
  bia_phase1 = next_phase1;
  bia_amplitude2 = next_amplitude2;
  bia_phase2 = next_phase2;
  bia_data_valid = true;
  last_bia_message_received_at_ms = current_time_ms;
  return true;
}

bool bia_input_timed_out() {
  if (!BIA_INPUT_ENABLED) {
    return false;
  }

  if (!bia_data_valid) {
    return current_time_ms >= BIA_INPUT_TIMEOUT_MS;
  }

  return current_time_ms - last_bia_message_received_at_ms > BIA_INPUT_TIMEOUT_MS;
}

void process_bia_message(char *message) {
  if (!parse_bia_message(message)) {
    bia_data_valid = false;
    set_error("ERR_BIA_BAD_MESSAGE", "invalid BIA JSON line");
    enter_state(ERROR_SAFE, "BIA_BAD_MESSAGE");
  }
}

void process_bia_serial() {
#if BIA_INPUT_ENABLED
  if (!BIA_INPUT_ENABLED) {
    return;
  }

  while (bia_serial.available() > 0) {
    char incoming = static_cast<char>(bia_serial.read());

    if (incoming == '\r') {
      continue;
    }

    if (incoming == '\n') {
      if (bia_message_length > 0) {
        bia_message_buffer[bia_message_length] = '\0';
        process_bia_message(bia_message_buffer);
        clear_bia_message_buffer();
      }
      continue;
    }

    if (bia_message_length < BIA_MESSAGE_BUFFER_SIZE - 1) {
      bia_message_buffer[bia_message_length++] = incoming;
    } else {
      bia_data_valid = false;
      clear_bia_message_buffer();
      set_error("ERR_BIA_MESSAGE_TOO_LONG", "BIA message exceeded buffer");
      enter_state(ERROR_SAFE, "BIA_MESSAGE_TOO_LONG");
    }
  }
#endif
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
  close_release_gate();

  if (state == RELEASING) {
    enter_state(COOLDOWN, next_event);
  } else if (state != ERROR_SAFE) {
    enter_state(IDLE, next_event);
  }
}

void handle_serial_command(char *command) {
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
  honey_amount_percent = simulated_honey_amount_percent;
  system_safe = simulated_system_safe;

  if (BIA_INPUT_ENABLED) {
    contact_input_source = "BIA_UART";
    paw_contact = false;

    if (bia_input_timed_out()) {
      set_error("ERR_BIA_TIMEOUT", "BIA input missing or stale");
      enter_state(ERROR_SAFE, "BIA_TIMEOUT");
    } else if (bia_data_valid) {
      paw_contact = bia_contact_detected;
    }
  } else {
    contact_input_source = "SIMULATED";
    paw_contact = simulated_paw_contact;
  }

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
    close_release_gate();
    set_error("ERR_EMERGENCY_STOP", "emergency_stop active");
    enter_state(ERROR_SAFE, "EMERGENCY_STOP");
    return;
  }

  if (!inputs_valid()) {
    demo_command_active = false;
    close_release_gate();
    enter_state(ERROR_SAFE, "INVALID_INPUT");
    return;
  }

  if (state == ERROR_SAFE) {
    close_release_gate();
    if (reset_requested && inputs_valid()) {
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
      } else if (!system_safe || !bear_detected || !paw_contact || !honey_enough) {
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
      enter_state(ERROR_SAFE, "ERROR");
      set_error("ERR_INVALID_STATE", "unknown state");
      break;
  }
}

void print_bool(bool value) {
  Serial.print(value ? F("true") : F("false"));
}

void print_nullable_bool(bool has_value, bool value) {
  if (has_value) {
    print_bool(value);
  } else {
    Serial.print(F("null"));
  }
}

void print_nullable_unsigned_long(bool has_value, unsigned long value) {
  if (has_value) {
    Serial.print(value);
  } else {
    Serial.print(F("null"));
  }
}

void print_raw_contact_value() {
  if (BIA_INPUT_ENABLED && bia_data_valid) {
    Serial.print(bia_amplitude1, 3);
  } else {
    Serial.print(F("null"));
  }
}

void print_nullable_string(const char *value) {
  if (value == NULL) {
    Serial.print(F("null"));
  } else {
    Serial.print(F("\""));
    Serial.print(value);
    Serial.print(F("\""));
  }
}

void emit_json_line() {
  Serial.print(F("{\"timestamp\":\"T+"));
  Serial.print(current_time_ms);
  Serial.print(F("ms\",\"state\":\""));
  Serial.print(state_to_string(state));
  Serial.print(F("\",\"previous_state\":\""));
  Serial.print(state_to_string(previous_state));
  Serial.print(F("\",\"event\":\""));
  Serial.print(event_name);
  Serial.print(F("\",\"bear_detected\":"));
  print_bool(bear_detected);
  Serial.print(F(",\"paw_contact\":"));
  print_bool(paw_contact);
  Serial.print(F(",\"contact_confirmed\":"));
  print_bool(contact_confirmed);
  Serial.print(F(",\"raw_contact_value\":"));
  print_raw_contact_value();
  Serial.print(F(",\"contact_input_source\":\""));
  Serial.print(contact_input_source);
  Serial.print(F("\",\"bia_input_enabled\":"));
  print_bool(BIA_INPUT_ENABLED);
  Serial.print(F(",\"bia_data_valid\":"));
  print_bool(BIA_INPUT_ENABLED && bia_data_valid && !bia_input_timed_out());
  Serial.print(F(",\"bia_data_age_ms\":"));
  print_nullable_unsigned_long(BIA_INPUT_ENABLED && bia_data_valid, current_time_ms - last_bia_message_received_at_ms);
  Serial.print(F(",\"bia_contact_detected\":"));
  print_nullable_bool(BIA_INPUT_ENABLED && bia_data_valid, bia_contact_detected);
  Serial.print(F(",\"bia_phase1\":"));
  if (BIA_INPUT_ENABLED && bia_data_valid) {
    Serial.print(bia_phase1, 3);
  } else {
    Serial.print(F("null"));
  }
  Serial.print(F(",\"bia_amplitude2\":"));
  if (BIA_INPUT_ENABLED && bia_data_valid) {
    Serial.print(bia_amplitude2, 3);
  } else {
    Serial.print(F("null"));
  }
  Serial.print(F(",\"bia_phase2\":"));
  if (BIA_INPUT_ENABLED && bia_data_valid) {
    Serial.print(bia_phase2, 3);
  } else {
    Serial.print(F("null"));
  }
  Serial.print(F(",\"honey_amount_percent\":"));
  Serial.print(honey_amount_percent);
  Serial.print(F(",\"honey_enough\":"));
  print_bool(honey_enough);
  Serial.print(F(",\"system_safe\":"));
  print_bool(system_safe);
  Serial.print(F(",\"emergency_stop\":"));
  print_bool(emergency_stop);
  Serial.print(F(",\"release_allowed\":"));
  print_bool(release_allowed);
  Serial.print(F(",\"release_state\":\""));
  Serial.print(release_state);
  Serial.print(F("\",\"actuator_open\":"));
  print_bool(actuator_open);
  Serial.print(F(",\"servo_angle\":"));
  Serial.print(current_servo_angle);
  Serial.print(F(",\"auto_test_mode\":"));
  print_bool(auto_test_mode);
  Serial.print(F(",\"error_code\":\""));
  Serial.print(error_code);
  Serial.print(F("\",\"error_message\":"));
  print_nullable_string(error_message);
  Serial.print(F("}"));
  Serial.println();
}

void update_outputs() {
  bool should_release = state == RELEASING;
  release_state = should_release ? "RELEASE_ON" : "RELEASE_OFF";

  digitalWrite(PIN_RELEASE_SIGNAL, should_release ? HIGH : LOW);
  digitalWrite(PIN_RELEASE_LED, should_release ? HIGH : LOW);
  digitalWrite(PIN_STATUS_LED, state == IDLE ? LOW : HIGH);

  if (should_release) {
    open_release_gate();
  } else {
    close_release_gate();
  }
}

void setup() {
  pinMode(PIN_RELEASE_LED, OUTPUT);
  pinMode(PIN_RELEASE_SIGNAL, OUTPUT);
  pinMode(PIN_STATUS_LED, OUTPUT);

  Serial.begin(SERIAL_BAUDRATE);
#if BIA_INPUT_ENABLED
  if (BIA_INPUT_ENABLED) {
    bia_serial.begin(BIA_SERIAL_BAUDRATE);
  }
#endif

  current_time_ms = millis();
  state_entered_at_ms = current_time_ms;
  simulation_step_started_at_ms = current_time_ms;
  clear_serial_command_buffer();
  clear_bia_message_buffer();
  init_release_actuator();

  update_inputs();
  update_outputs();
  emit_json_line();
}

void loop() {
  current_time_ms = millis();
  process_serial_commands();
  process_bia_serial();

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
