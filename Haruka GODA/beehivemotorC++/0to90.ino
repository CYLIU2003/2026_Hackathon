#include <Servo.h>

Servo servo;

const int buttonPin = 2;  // Manual simulated bear detection button
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

int currentServoAngle = closedAngle;
int lastButtonState = HIGH;
int buttonState = HIGH;
unsigned long lastDebounceTimeMs = 0;
unsigned long lastDispenseTimeMs = 0;
bool hasDispensed = false;
bool aiBearDetectedLatched = false;
String serialBuffer = "";

void handleSerialInput();
void processCommand(String command);
void handleButtonInput();
void handleBearDetected(const char *sourceEvent);
void runDispenseCycle(const char *sourceEvent);
void moveServoSmooth(int targetAngle);
void moveToClosedPosition();
bool commandMeansBearDetected(const String &command);
bool commandMeansBearCleared(const String &command);
bool commandMeansRelease(const String &command);
bool commandMeansStop(const String &command);
unsigned long cooldownRemainingMs();
void emitStatus(const char *eventName, const char *releaseState);

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
}

void handleSerialInput() {
  while (Serial.available() > 0) {
    char incoming = (char)Serial.read();
    if (incoming == '\n' || incoming == '\r') {
      if (serialBuffer.length() > 0) {
        processCommand(serialBuffer);
        serialBuffer = "";
      }
    } else if (serialBuffer.length() < 160) {
      serialBuffer += incoming;
    } else {
      serialBuffer = "";
      emitStatus("SERIAL_COMMAND_TOO_LONG_RELEASE_OFF", "RELEASE_OFF");
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

  if (commandMeansRelease(normalized)) {
    handleBearDetected("DETECTED_DISPENSING_SERIAL_RELEASE");
  } else if (commandMeansBearDetected(normalized)) {
    if (!aiBearDetectedLatched) {
      aiBearDetectedLatched = true;
      handleBearDetected("DETECTED_DISPENSING_AI_BEAR");
    } else {
      emitStatus("AI_BEAR_STILL_DETECTED_NO_REPEAT", "RELEASE_OFF");
    }
  } else if (commandMeansBearCleared(normalized)) {
    aiBearDetectedLatched = false;
    emitStatus("AI_BEAR_CLEAR_RELEASE_OFF", "RELEASE_OFF");
  } else if (commandMeansStop(normalized)) {
    aiBearDetectedLatched = false;
    moveToClosedPosition();
    emitStatus("SAFE_STOP_RELEASE_OFF", "RELEASE_OFF");
  } else if (normalized == "RESET") {
    aiBearDetectedLatched = false;
    moveToClosedPosition();
    emitStatus("RESET_READY_RELEASE_OFF", "RELEASE_OFF");
  } else if (normalized == "TEST_AUTO_OFF" || normalized == "STATUS") {
    emitStatus("STATUS_RELEASE_OFF", "RELEASE_OFF");
  } else {
    emitStatus("UNKNOWN_COMMAND_RELEASE_OFF", "RELEASE_OFF");
  }
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
        handleBearDetected("DETECTED_DISPENSING_BUTTON");
      }
    }
  }

  lastButtonState = reading;
}

void handleBearDetected(const char *sourceEvent) {
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

bool commandMeansRelease(const String &command) {
  return command == "RELEASE" ||
         command == "OPEN" ||
         command == "TEST" ||
         command == "TEST_MOTION";
}

bool commandMeansStop(const String &command) {
  return command == "STOP" ||
         command == "CLOSE" ||
         command == "EMERGENCY_STOP" ||
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

void emitStatus(const char *eventName, const char *releaseState) {
  Serial.print(F("{\"uptime_ms\":"));
  Serial.print(millis());
  Serial.print(F(",\"source\":\"goda_0to90_actuator\""));
  Serial.print(F(",\"event\":\""));
  Serial.print(eventName);
  Serial.print(F("\",\"release_state\":\""));
  Serial.print(releaseState);
  Serial.print(F("\",\"servo_angle\":"));
  Serial.print(currentServoAngle);
  Serial.print(F(",\"cooldown_remaining_ms\":"));
  Serial.print(cooldownRemainingMs());
  Serial.print(F(",\"message_en\":\"Detected -> Dispensing\""));
  Serial.print(F(",\"message_ja\":\"検出済み -> 排出します\""));
  Serial.println(F("}"));
}
