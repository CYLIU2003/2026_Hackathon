#include <Arduino.h>
#include "config.h"

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

int simulation_step = 0;
unsigned long simulation_step_started_at_ms = 0;

unsigned long current_time_ms = 0;
unsigned long state_entered_at_ms = 0;
unsigned long last_contact_time_ms = 0;
unsigned long release_started_at_ms = 0;
unsigned long cooldown_started_at_ms = 0;
unsigned long last_message_sent_at_ms = 0;
unsigned long last_sensor_update_at_ms = 0;

const unsigned long SIMULATION_STEP_DURATION_MS = 5000;
char serial_command_buffer[32];
int serial_command_length = 0;

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

void handle_serial_command(const char *command) {
  if (strcmp(command, "RESET") == 0) {
    if (state == ERROR_SAFE) {
      request_reset();
      event_name = "RESET_REQUEST";
    }
  }
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
    set_error("ERR_EMERGENCY_STOP", "emergency_stop active");
    enter_state(ERROR_SAFE, "EMERGENCY_STOP");
    return;
  }

  if (!inputs_valid()) {
    enter_state(ERROR_SAFE, "INVALID_INPUT");
    return;
  }

  if (state == ERROR_SAFE) {
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
        enter_state(COOLDOWN, "RELEASE_ABORTED");
      } else if (!system_safe || !bear_detected || !paw_contact || !honey_enough) {
        enter_state(COOLDOWN, "RELEASE_ABORTED");
      } else if (current_time_ms - release_started_at_ms >= MAX_RELEASE_DURATION_MS) {
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
  Serial.print("\",\"error_code\":\"");
  Serial.print(error_code);
  Serial.print("\",\"error_message\":");
  print_nullable_string(error_message);
  Serial.print("}");
  Serial.println();
}

void update_outputs() {
  release_state = (state == RELEASING) ? "RELEASE_ON" : "RELEASE_OFF";
  digitalWrite(PIN_RELEASE_SIGNAL, state == RELEASING ? HIGH : LOW);
  digitalWrite(PIN_RELEASE_LED, state == RELEASING ? HIGH : LOW);
  digitalWrite(PIN_STATUS_LED, state == IDLE ? LOW : HIGH);
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
