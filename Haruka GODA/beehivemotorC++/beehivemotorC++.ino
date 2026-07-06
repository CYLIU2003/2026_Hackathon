#include <Arduino.h>

#define MOTOR_MODE_PCA9685_SERVO 1
#define MOTOR_MODE_L293D_STEPPER 2

// Arduino IDEで切り替える場合は、次の行のモード名を変更してください。
#ifndef ACTIVE_MOTOR_MODE
#define ACTIVE_MOTOR_MODE MOTOR_MODE_L293D_STEPPER
#endif

#if ACTIVE_MOTOR_MODE == MOTOR_MODE_PCA9685_SERVO
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#elif ACTIVE_MOTOR_MODE != MOTOR_MODE_L293D_STEPPER
#error "ACTIVE_MOTOR_MODE must be MOTOR_MODE_PCA9685_SERVO or MOTOR_MODE_L293D_STEPPER"
#endif

const int buttonPin = 2;
const int ledPin = 13;  // 内蔵LED（デバッグ用）

int motorState = 0;  // 0 = close/origin, 1 = open
int lastButtonState = HIGH;
int buttonState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 50;

unsigned long lastBlinkTime = 0;

#if ACTIVE_MOTOR_MODE == MOTOR_MODE_PCA9685_SERVO
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x70);  // I2C address = 0x70

const uint8_t servoNum = 0;
const int servoMinPulse = 150;
const int servoMaxPulse = 500;
const int servoClosedAngle = 0;
const int servoOpenAngle = 90;
const int servoStepDegrees = 10;
const int servoStepDelayMs = 30;

bool pwmAvailable = false;  // PCA9685 が使えるかどうか
#endif

#if ACTIVE_MOTOR_MODE == MOTOR_MODE_L293D_STEPPER
// L293D bare IC -> Arduino Uno
// 1,2EN:D5, 1A:D8, 2A:D9, 3,4EN:D6, 3A:D10, 4A:D11
// L293D VCC1:5V logic, VCC2:motor power, GND:Arduino GNDと共通
const int l293dEnablePinA = 5;
const int l293dInputPin1 = 8;
const int l293dInputPin2 = 9;
const int l293dEnablePinB = 6;
const int l293dInputPin3 = 10;
const int l293dInputPin4 = 11;

// 4-wire bipolar stepper + L293Dの2相励磁。開閉量は実機に合わせて調整してください。
const long stepperOpenSteps = 50;  // about 90 degrees for a common 1.8-degree stepper
const unsigned int stepperStepDelayMs = 5;
const bool releaseStepperCoilsAfterMove = true;  // 発熱を抑えるため既定はOFF保持しない

const uint8_t l293dFullStepSequence[][4] = {
  {1, 0, 1, 0},
  {0, 1, 1, 0},
  {0, 1, 0, 1},
  {1, 0, 0, 1}
};
const int stepperSequenceLength = sizeof(l293dFullStepSequence) / sizeof(l293dFullStepSequence[0]);

long stepperCurrentPosition = 0;
int stepperSequenceIndex = 0;
#endif

const char *getMotorModeName();
bool isActuatorAvailable();
void initializeMotor();
void moveMotorToOpenPosition();
void moveMotorToClosedPosition();
void handleButtonPressed();

#if ACTIVE_MOTOR_MODE == MOTOR_MODE_PCA9685_SERVO
int angleToPulse(int angle);
void moveServoSmooth(int startAngle, int targetAngle);
#endif

#if ACTIVE_MOTOR_MODE == MOTOR_MODE_L293D_STEPPER
void setupStepperPins();
void writeStepperOutputs(int sequenceIndex);
void enableStepperDriver();
void releaseStepperCoils();
void stepStepperOnce(int direction);
void moveStepperToPosition(long targetPosition);
#endif

void setup() {
  Serial.begin(9600);
  Serial.println("--- Starting Setup ---");

  pinMode(buttonPin, INPUT_PULLUP);
  pinMode(ledPin, OUTPUT);

  // 起動確認：LEDを3回点滅
  for (int i = 0; i < 3; i++) {
    digitalWrite(ledPin, HIGH);
    delay(100);
    digitalWrite(ledPin, LOW);
    delay(100);
  }
  Serial.println("LED blink OK");

  initializeMotor();

  Serial.print("Motor mode: ");
  Serial.println(getMotorModeName());
  Serial.print("Button pin: ");
  Serial.print(buttonPin);
  Serial.print(" initial=");
  Serial.println(digitalRead(buttonPin));
  Serial.println("--- System Ready ---");
}

void loop() {
  // === 生存確認：500ms ごとにLED点滅 ===
  if (millis() - lastBlinkTime > 500) {
    lastBlinkTime = millis();
    digitalWrite(ledPin, !digitalRead(ledPin));
  }

  int reading = digitalRead(buttonPin);

  // チャタリング除去
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading != buttonState) {
      buttonState = reading;

      // ボタンが押された瞬間（HIGH→LOW）
      if (buttonState == LOW) {
        handleButtonPressed();
      }
    }
  }

  lastButtonState = reading;
}

const char *getMotorModeName() {
#if ACTIVE_MOTOR_MODE == MOTOR_MODE_PCA9685_SERVO
  return "PCA9685_SERVO";
#else
  return "L293D_STEPPER";
#endif
}

bool isActuatorAvailable() {
#if ACTIVE_MOTOR_MODE == MOTOR_MODE_PCA9685_SERVO
  return pwmAvailable;
#else
  return true;
#endif
}

void initializeMotor() {
#if ACTIVE_MOTOR_MODE == MOTOR_MODE_PCA9685_SERVO
  // === I2C 初期化 ===
  Wire.begin();
  Serial.println("I2C initialized");

  // === PCA9685 初期化（アドレス 0x70、失敗しても続行） ===
  Serial.print("Initializing PCA9685 at 0x70... ");
  if (pwm.begin()) {
    pwm.setOscillatorFrequency(27000000);
    pwm.setPWMFreq(50);
    pwm.setPWM(servoNum, 0, angleToPulse(servoClosedAngle));
    pwmAvailable = true;
    Serial.println("OK");
  } else {
    pwmAvailable = false;
    Serial.println("NOT FOUND (button+LED only mode)");
  }
#else
  setupStepperPins();
  releaseStepperCoils();
  Serial.println("L293D stepper initialized");
  Serial.println("Power-on position is treated as CLOSED/origin.");
  Serial.println("Wire L293D ENA:D5 IN1:D8 IN2:D9 ENB:D6 IN3:D10 IN4:D11.");
#endif
}

void handleButtonPressed() {
  Serial.print("Button Pressed! motorState=");
  Serial.print(motorState);
  Serial.print(" motorMode=");
  Serial.print(getMotorModeName());
  Serial.print(" actuatorAvailable=");
  Serial.println(isActuatorAvailable());

  if (motorState == 0) {
    Serial.println("-> Moving to OPEN position");
    if (isActuatorAvailable()) {
      moveMotorToOpenPosition();
    }
    motorState = 1;
  } else {
    Serial.println("-> Moving to CLOSED position");
    if (isActuatorAvailable()) {
      moveMotorToClosedPosition();
    }
    motorState = 0;
  }
}

void moveMotorToOpenPosition() {
#if ACTIVE_MOTOR_MODE == MOTOR_MODE_PCA9685_SERVO
  moveServoSmooth(servoClosedAngle, servoOpenAngle);
#else
  moveStepperToPosition(stepperOpenSteps);
#endif
}

void moveMotorToClosedPosition() {
#if ACTIVE_MOTOR_MODE == MOTOR_MODE_PCA9685_SERVO
  moveServoSmooth(servoOpenAngle, servoClosedAngle);
#else
  moveStepperToPosition(0);
#endif
}

#if ACTIVE_MOTOR_MODE == MOTOR_MODE_PCA9685_SERVO
int angleToPulse(int angle) {
  angle = constrain(angle, 0, 180);
  return map(angle, 0, 180, servoMinPulse, servoMaxPulse);
}

void moveServoSmooth(int startAngle, int targetAngle) {
  int direction = (targetAngle >= startAngle) ? 1 : -1;

  for (int angle = startAngle; angle != targetAngle; angle += direction * servoStepDegrees) {
    pwm.setPWM(servoNum, 0, angleToPulse(angle));
    delay(servoStepDelayMs);

    if ((direction > 0 && angle + servoStepDegrees > targetAngle) ||
        (direction < 0 && angle - servoStepDegrees < targetAngle)) {
      break;
    }
  }

  pwm.setPWM(servoNum, 0, angleToPulse(targetAngle));
}
#endif

#if ACTIVE_MOTOR_MODE == MOTOR_MODE_L293D_STEPPER
void setupStepperPins() {
  pinMode(l293dEnablePinA, OUTPUT);
  pinMode(l293dInputPin1, OUTPUT);
  pinMode(l293dInputPin2, OUTPUT);
  pinMode(l293dEnablePinB, OUTPUT);
  pinMode(l293dInputPin3, OUTPUT);
  pinMode(l293dInputPin4, OUTPUT);
}

void writeStepperOutputs(int sequenceIndex) {
  digitalWrite(l293dInputPin1, l293dFullStepSequence[sequenceIndex][0]);
  digitalWrite(l293dInputPin2, l293dFullStepSequence[sequenceIndex][1]);
  digitalWrite(l293dInputPin3, l293dFullStepSequence[sequenceIndex][2]);
  digitalWrite(l293dInputPin4, l293dFullStepSequence[sequenceIndex][3]);
}

void enableStepperDriver() {
  digitalWrite(l293dEnablePinA, HIGH);
  digitalWrite(l293dEnablePinB, HIGH);
}

void releaseStepperCoils() {
  digitalWrite(l293dInputPin1, LOW);
  digitalWrite(l293dInputPin2, LOW);
  digitalWrite(l293dInputPin3, LOW);
  digitalWrite(l293dInputPin4, LOW);
  digitalWrite(l293dEnablePinA, LOW);
  digitalWrite(l293dEnablePinB, LOW);
}

void stepStepperOnce(int direction) {
  stepperSequenceIndex += direction;
  if (stepperSequenceIndex >= stepperSequenceLength) {
    stepperSequenceIndex = 0;
  } else if (stepperSequenceIndex < 0) {
    stepperSequenceIndex = stepperSequenceLength - 1;
  }

  enableStepperDriver();
  writeStepperOutputs(stepperSequenceIndex);
  delay(stepperStepDelayMs);
  stepperCurrentPosition += direction;
}

void moveStepperToPosition(long targetPosition) {
  while (stepperCurrentPosition != targetPosition) {
    int direction = (targetPosition > stepperCurrentPosition) ? 1 : -1;
    stepStepperOnce(direction);
  }

  if (releaseStepperCoilsAfterMove) {
    releaseStepperCoils();
  }
}
#endif
