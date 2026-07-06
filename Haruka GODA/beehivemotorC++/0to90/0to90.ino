// Integrated direct-servo actuator sketch for Raspberry Pi -> Arduino Uno demos.
#include <Servo.h>

Servo servo;

const int buttonPin = 2;  // Manual simulated safe-release button
const int servoPin = 3;   // Servo signal pin
const int ledPin = 13;    // Built-in LED: ON while dispensing

const int closedAngle = 0;
const int dispenseAngle = 90;
const int servoStepDegrees = 10;
const unsigned long servoStepDelayMs = 30;
const unsigned long dispenseHoldMs = 700;
const unsigned long dispenseCooldownMs = 10000;  // Maximum once per 10 seconds
const unsigned long debounceDelayMs = 50;
const unsigned long serialBaudrate = 115200;

const int honeyMinThresholdPercent = 20;
const int defaultHoneyAmountPercent = 80;
const unsigned long contactConfirmDurationMs = 500;
const unsigned long statusIntervalMs = 1000;

int currentServoAngle = closedAngle;
int lastButtonState = HIGH;
int buttonState = HIGH;
unsigned long lastDebounceTimeMs = 0;
unsigned long lastDispenseTimeMs = 0;
unsigned long contactStartedAtMs = 0;
unsigned long lastStatusTimeMs = 0;
bool hasDispensed = false;
bool releaseConsumedForCurrentContact = false;
String serialBuffer = "";

bool bearDetected = false;
bool pawContact = false;
int honeyAmountPercent = defaultHoneyAmountPercent;
bool systemSafe = true;
bool emergencyStop = false;
bool contactConfirmed = false;
bool errorSafe = false;
const char *errorCode = "ERR_NONE";
const char *errorMessage = "";

void handleSerialInput();
void processCommand(String command);
bool handleSetCommand(const String &command);
void handleButtonInput();
void requestIntegratedDemoRelease(const char *sourceEvent);
void clearMotionInputs();
void evaluateIntegratedRelease(const char *sourceEvent);
void handleSafeReleaseRequest(const char *sourceEvent);
void runDispenseCycle(const char *sourceEvent);
void moveServoSmooth(int targetAngle);
void moveToClosedPosition();
void updateContactConfirmation();
bool releaseAllowedNow();
bool inputsValid();
void enterErrorSafe(const char *code, const char *message, const char *sourceEvent);
void clearErrorSafe();
bool commandMeansBearDetected(const String &command);
bool commandMeansBearCleared(const String &command);
bool commandMeansRelease(const String &command);
bool commandMeansStop(const String &command);
bool commandMeansEmergencyStop(const String &command);
unsigned long cooldownRemainingMs();
void emitStatus(const char *eventName, const char *releaseState);
void emitPeriodicStatus();
void printBool(bool value);
void printJsonStringValue(const char *value);

void setup() {
  Serial.begin(serialBaudrate);

  pinMode(buttonPin, INPUT_PULLUP);
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);

  servo.attach(servoPin);
  servo.write(closedAngle);
  currentServoAngle = closedAngle;

  emitStatus("BOOT_READY_RELEASE_OFF", "RELEASE_OFF");
}

void loop() {
  handleSerialInput();
  handleButtonInput();
  evaluateIntegratedRelease("SYSTEM_RELEASE_START");
  emitPeriodicStatus();
}

void handleSerialInput() {
  while (Serial.available() > 0) {
    char incoming = (char)Serial.read();
    if (incoming == '\n' || incoming == '\r') {
      if (serialBuffer.length() > 0) {
        processCommand(serialBuffer);
        serialBuffer = "";
      }
    } else if (serialBuffer.length() < 180) {
      serialBuffer += incoming;
    } else {
      serialBuffer = "";
      enterErrorSafe("ERR_SERIAL_COMMAND_TOO_LONG", "serial command exceeded buffer", "SERIAL_COMMAND_TOO_LONG");
    }
  }
}

void processCommand(String command) {
  command.trim();
  if (command.length() == 0) {
    return;
  }

  String normalized = command;
  normalized.toUpperCase();

  if (normalized.startsWith("SET ")) {
    if (handleSetCommand(normalized)) {
      evaluateIntegratedRelease("SYSTEM_RELEASE_START");
    }
    return;
  }

  if (commandMeansEmergencyStop(normalized)) {
    emergencyStop = true;
    enterErrorSafe("ERR_EMERGENCY_STOP", "emergency_stop active", "SERIAL_ESTOP_RELEASE_OFF");
  } else if (commandMeansStop(normalized)) {
    emergencyStop = false;
    clearMotionInputs();
    moveToClosedPosition();
    emitStatus("SAFE_STOP_RELEASE_OFF", "RELEASE_OFF");
  } else if (normalized == "RESET") {
    clearErrorSafe();
    emergencyStop = false;
    releaseConsumedForCurrentContact = false;
    moveToClosedPosition();
    emitStatus("RESET_READY_RELEASE_OFF", "RELEASE_OFF");
  } else if (commandMeansRelease(normalized)) {
    requestIntegratedDemoRelease("DEMO_RELEASE_COMMAND");
  } else if (commandMeansBearDetected(normalized)) {
    bearDetected = true;
    emitStatus("SERIAL_AI_BEAR_ON_RELEASE_OFF", "RELEASE_OFF");
  } else if (commandMeansBearCleared(normalized)) {
    bearDetected = false;
    pawContact = false;
    contactConfirmed = false;
    contactStartedAtMs = 0;
    releaseConsumedForCurrentContact = false;
    emitStatus("AI_BEAR_CLEAR_RELEASE_OFF", "RELEASE_OFF");
  } else if (normalized == "STATUS" || normalized == "TEST_AUTO_OFF") {
    emitStatus("STATUS_RELEASE_OFF", "RELEASE_OFF");
  } else {
    enterErrorSafe("ERR_UNKNOWN_COMMAND", "unknown serial command", "UNKNOWN_COMMAND_RELEASE_OFF");
  }
}

bool handleSetCommand(const String &command) {
  char key[24];
  int value = 0;
  int parsed = sscanf(command.c_str() + 4, "%23s %d", key, &value);
  if (parsed != 2) {
    enterErrorSafe("ERR_BAD_SET_COMMAND", "expected SET KEY VALUE", "BAD_SET_COMMAND_RELEASE_OFF");
    return false;
  }

  if (strcmp(key, "AI_BEAR") == 0 || strcmp(key, "BEAR") == 0) {
    bearDetected = value != 0;
    if (!bearDetected) {
      releaseConsumedForCurrentContact = false;
    }
  } else if (strcmp(key, "PAW") == 0 || strcmp(key, "CONTACT") == 0) {
    pawContact = value != 0;
    if (!pawContact) {
      contactConfirmed = false;
      contactStartedAtMs = 0;
      releaseConsumedForCurrentContact = false;
    }
  } else if (strcmp(key, "HONEY") == 0) {
    honeyAmountPercent = value;
    if (!inputsValid()) {
      enterErrorSafe("ERR_INVALID_HONEY_AMOUNT", "honey_amount_percent out of range", "INVALID_HONEY_RELEASE_OFF");
      return false;
    }
  } else if (strcmp(key, "SAFE") == 0) {
    systemSafe = value != 0;
  } else if (strcmp(key, "ESTOP") == 0 || strcmp(key, "EMERGENCY") == 0) {
    emergencyStop = value != 0;
    if (emergencyStop) {
      enterErrorSafe("ERR_EMERGENCY_STOP", "emergency_stop active", "SERIAL_ESTOP_RELEASE_OFF");
      return false;
    }
  } else {
    enterErrorSafe("ERR_UNKNOWN_SET_KEY", "unknown SET key", "UNKNOWN_SET_KEY_RELEASE_OFF");
    return false;
  }

  emitStatus("SERIAL_SET_INPUT_RELEASE_OFF", "RELEASE_OFF");
  return true;
}

void handleButtonInput() {
  int reading = digitalRead(buttonPin);

  if (reading != lastButtonState) {
    lastDebounceTimeMs = millis();
  }

  if ((millis() - lastDebounceTimeMs) > debounceDelayMs) {
    if (reading != buttonState) {
      buttonState = reading;

      if (buttonState == LOW) {
        requestIntegratedDemoRelease("DEMO_BUTTON_COMMAND");
      }
    }
  }

  lastButtonState = reading;
}

void requestIntegratedDemoRelease(const char *sourceEvent) {
  if (errorSafe) {
    emitStatus("DEMO_RELEASE_BLOCKED_ERROR_SAFE", "RELEASE_OFF");
    return;
  }

  bearDetected = true;
  pawContact = true;
  honeyAmountPercent = defaultHoneyAmountPercent;
  if (honeyAmountPercent < honeyMinThresholdPercent) {
    honeyAmountPercent = honeyMinThresholdPercent;
  }
  systemSafe = true;
  emergencyStop = false;
  contactConfirmed = false;
  contactStartedAtMs = 0;
  releaseConsumedForCurrentContact = false;
  emitStatus(sourceEvent, "RELEASE_OFF");
}

void clearMotionInputs() {
  bearDetected = false;
  pawContact = false;
  contactConfirmed = false;
  contactStartedAtMs = 0;
  releaseConsumedForCurrentContact = false;
}

void evaluateIntegratedRelease(const char *sourceEvent) {
  updateContactConfirmation();

  if (!bearDetected || !pawContact) {
    releaseConsumedForCurrentContact = false;
  }

  if (!inputsValid()) {
    enterErrorSafe("ERR_INVALID_HONEY_AMOUNT", "honey_amount_percent out of range", "INVALID_HONEY_RELEASE_OFF");
    return;
  }

  if (emergencyStop) {
    enterErrorSafe("ERR_EMERGENCY_STOP", "emergency_stop active", "EMERGENCY_STOP_RELEASE_OFF");
    return;
  }

  if (errorSafe) {
    moveToClosedPosition();
    return;
  }

  if (releaseAllowedNow() && !releaseConsumedForCurrentContact) {
    releaseConsumedForCurrentContact = true;
    handleSafeReleaseRequest(sourceEvent);
  }
}

void handleSafeReleaseRequest(const char *sourceEvent) {
  if (errorSafe || emergencyStop || !systemSafe) {
    emitStatus("RELEASE_BLOCKED_RELEASE_OFF", "RELEASE_OFF");
    return;
  }

  if (hasDispensed && (millis() - lastDispenseTimeMs < dispenseCooldownMs)) {
    emitStatus("COOLDOWN_BLOCKED_RELEASE_OFF", "RELEASE_OFF");
    return;
  }

  runDispenseCycle(sourceEvent);
}

void runDispenseCycle(const char *sourceEvent) {
  emitStatus(sourceEvent, "RELEASE_ON");
  digitalWrite(ledPin, HIGH);

  moveServoSmooth(closedAngle);
  moveServoSmooth(dispenseAngle);
  delay(dispenseHoldMs);
  moveServoSmooth(closedAngle);

  digitalWrite(ledPin, LOW);
  lastDispenseTimeMs = millis();
  hasDispensed = true;
  emitStatus("DISPENSE_DONE_COOLDOWN_RELEASE_OFF", "RELEASE_OFF");
}

void moveServoSmooth(int targetAngle) {
  targetAngle = constrain(targetAngle, 0, 180);
  if (currentServoAngle == targetAngle) {
    servo.write(targetAngle);
    return;
  }

  int direction = (targetAngle > currentServoAngle) ? 1 : -1;
  while (currentServoAngle != targetAngle) {
    currentServoAngle += direction * servoStepDegrees;
    if ((direction > 0 && currentServoAngle > targetAngle) ||
        (direction < 0 && currentServoAngle < targetAngle)) {
      currentServoAngle = targetAngle;
    }
    servo.write(currentServoAngle);
    delay(servoStepDelayMs);
  }
}

void moveToClosedPosition() {
  moveServoSmooth(closedAngle);
  digitalWrite(ledPin, LOW);
}

void updateContactConfirmation() {
  if (!pawContact) {
    contactStartedAtMs = 0;
    contactConfirmed = false;
    return;
  }

  if (contactStartedAtMs == 0) {
    contactStartedAtMs = millis();
  }

  if (millis() - contactStartedAtMs >= contactConfirmDurationMs) {
    contactConfirmed = true;
  }
}

bool releaseAllowedNow() {
  return bearDetected &&
         pawContact &&
         contactConfirmed &&
         honeyAmountPercent >= honeyMinThresholdPercent &&
         systemSafe &&
         !emergencyStop &&
         !errorSafe;
}

bool inputsValid() {
  return honeyAmountPercent >= 0 && honeyAmountPercent <= 100;
}

void enterErrorSafe(const char *code, const char *message, const char *sourceEvent) {
  bool wasErrorSafe = errorSafe;
  errorSafe = true;
  errorCode = code;
  errorMessage = message;
  moveToClosedPosition();
  if (!wasErrorSafe) {
    emitStatus(sourceEvent, "RELEASE_OFF");
  }
}

void clearErrorSafe() {
  errorSafe = false;
  errorCode = "ERR_NONE";
  errorMessage = "";
}

bool commandMeansRelease(const String &command) {
  return command == "RELEASE" ||
         command == "OPEN" ||
         command == "TEST" ||
         command == "TEST_MOTION";
}

bool commandMeansStop(const String &command) {
  return command == "STOP" ||
         command == "CLOSE";
}

bool commandMeansEmergencyStop(const String &command) {
  return command == "EMERGENCY_STOP" ||
         command == "ESTOP";
}

bool commandMeansBearDetected(const String &command) {
  return command == "AI_BEAR_DETECTED" ||
         command == "BEAR_DETECTED" ||
         command == "DETECTED" ||
         command == "SET AI_BEAR 1" ||
         command == "SET BEAR 1" ||
         command.indexOf("\"AI_BEAR_DETECTED\":TRUE") >= 0 ||
         command.indexOf("\"BEAR_DETECTED\":TRUE") >= 0 ||
         command.indexOf("\"EVENT\":\"AI_BEAR_DETECTED\"") >= 0;
}

bool commandMeansBearCleared(const String &command) {
  return command == "AI_NO_BEAR" ||
         command == "NO_BEAR" ||
         command == "SET AI_BEAR 0" ||
         command == "SET BEAR 0" ||
         command.indexOf("\"AI_BEAR_DETECTED\":FALSE") >= 0 ||
         command.indexOf("\"BEAR_DETECTED\":FALSE") >= 0 ||
         command.indexOf("\"EVENT\":\"AI_NO_BEAR\"") >= 0;
}

unsigned long cooldownRemainingMs() {
  if (!hasDispensed) {
    return 0;
  }

  unsigned long elapsedMs = millis() - lastDispenseTimeMs;
  if (elapsedMs >= dispenseCooldownMs) {
    return 0;
  }
  return dispenseCooldownMs - elapsedMs;
}

void emitPeriodicStatus() {
  if (millis() - lastStatusTimeMs >= statusIntervalMs) {
    emitStatus(errorSafe ? "ERROR_SAFE_STATUS" : "STATUS_RELEASE_OFF", "RELEASE_OFF");
  }
}

void printBool(bool value) {
  Serial.print(value ? F("true") : F("false"));
}

void printJsonStringValue(const char *value) {
  Serial.print(F("\""));
  Serial.print(value);
  Serial.print(F("\""));
}

void emitStatus(const char *eventName, const char *releaseState) {
  lastStatusTimeMs = millis();
  bool honeyEnough = honeyAmountPercent >= honeyMinThresholdPercent;
  unsigned long remainingCooldownMs = cooldownRemainingMs();
  const char *stateName = "IDLE";
  if (errorSafe) {
    stateName = "ERROR_SAFE";
  } else if (strcmp(releaseState, "RELEASE_ON") == 0) {
    stateName = "RELEASING";
  } else if (remainingCooldownMs > 0) {
    stateName = "COOLDOWN";
  }

  Serial.print(F("{\"uptime_ms\":"));
  Serial.print(millis());
  Serial.print(F(",\"source\":\"goda_0to90_integrated_actuator\""));
  Serial.print(F(",\"state\":\""));
  Serial.print(stateName);
  Serial.print(F("\""));
  Serial.print(F(",\"event\":\""));
  Serial.print(eventName);
  Serial.print(F("\",\"release_state\":\""));
  Serial.print(releaseState);
  Serial.print(F("\",\"bear_detected\":"));
  printBool(bearDetected);
  Serial.print(F(",\"paw_contact\":"));
  printBool(pawContact);
  Serial.print(F(",\"contact_confirmed\":"));
  printBool(contactConfirmed);
  Serial.print(F(",\"honey_amount_percent\":"));
  Serial.print(honeyAmountPercent);
  Serial.print(F(",\"honey_enough\":"));
  printBool(honeyEnough);
  Serial.print(F(",\"system_safe\":"));
  printBool(systemSafe);
  Serial.print(F(",\"emergency_stop\":"));
  printBool(emergencyStop);
  Serial.print(F(",\"release_allowed\":"));
  printBool(releaseAllowedNow());
  Serial.print(F(",\"error_safe\":"));
  printBool(errorSafe);
  Serial.print(F(",\"error_code\":"));
  printJsonStringValue(errorCode);
  Serial.print(F(",\"error_message\":"));
  printJsonStringValue(errorMessage);
  Serial.print(F(",\"servo_angle\":"));
  Serial.print(currentServoAngle);
  Serial.print(F(",\"cooldown_remaining_ms\":"));
  Serial.print(remainingCooldownMs);
  Serial.print(F(",\"message_en\":\"Integrated safety inputs -> 0 to 90 actuator\""));
  Serial.print(F(",\"message_ja\":\"安全入力統合 -> 0度から90度の放出動作\""));
  Serial.println(F("}"));
}
