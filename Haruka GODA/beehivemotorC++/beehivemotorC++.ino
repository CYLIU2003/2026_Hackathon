#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x70);  // I2C address = 0x70

#define SERVOMIN  150 
#define SERVOMAX  500 

uint8_t servoNum = 0; 
const int buttonPin = 2;
const int ledPin = 13;  // 内蔵LED（デバッグ用）

int motorState = 0;      
int lastButtonState = HIGH; 
int buttonState = HIGH;
unsigned long lastDebounceTime = 0;  
unsigned long debounceDelay = 50;
bool pwmAvailable = false;  // PCA9685 が使えるかどうか

unsigned long lastBlinkTime = 0;

void setup() {
  Serial.begin(9600);
  Serial.println("--- Starting Setup ---");
  
  pinMode(buttonPin, INPUT_PULLUP);
  pinMode(ledPin, OUTPUT);
  
  // 起動確認：LEDを3回点滅
  for (int i = 0; i < 3; i++) {
    digitalWrite(ledPin, HIGH); delay(100);
    digitalWrite(ledPin, LOW);  delay(100);
  }
  Serial.println("LED blink OK");

  // === I2C 初期化 ===
  Wire.begin();
  Serial.println("I2C initialized");

  // === PCA9685 初期化（アドレス 0x70、失敗しても続行） ===
  Serial.print("Initializing PCA9685 at 0x70... ");
  if (pwm.begin()) {
    pwm.setOscillatorFrequency(27000000);
    pwm.setPWMFreq(50);  
    pwm.setPWM(servoNum, 0, angleToPulse(0));
    pwmAvailable = true;
    Serial.println("OK");
  } else {
    pwmAvailable = false;
    Serial.println("NOT FOUND (button+LED only mode)");
  }

  Serial.print("Button pin: ");
  Serial.print(buttonPin);
  Serial.print(" initial=");
  Serial.println(digitalRead(buttonPin));
  Serial.println("--- System Ready ---");
}

int angleToPulse(int angle) {
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
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
        Serial.print("Button Pressed! motorState=");
        Serial.print(motorState);
        Serial.print(" pwmAvailable=");
        Serial.println(pwmAvailable);

        if (motorState == 0) {
          Serial.println("-> Moving to 90 degrees");
          if (pwmAvailable) {
            for (int angle = 0; angle <= 90; angle += 10) {
              pwm.setPWM(servoNum, 0, angleToPulse(angle));
              delay(30);
            }
          }
          motorState = 1; 
        } 
        else if (motorState == 1) {
          Serial.println("-> Moving to 0 degrees");
          if (pwmAvailable) {
            for (int angle = 90; angle >= 0; angle -= 10) {
              pwm.setPWM(servoNum, 0, angleToPulse(angle));
              delay(30);
            }
          }
          motorState = 0; 
        }
      }
    }
  }

  lastButtonState = reading;
}