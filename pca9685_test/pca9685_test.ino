#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x70);

void setup() {
  Serial.begin(9600);
  delay(100);
  
  Serial.println("=== PCA9685 Test ===");
  
  // 1. Wire.beginせずにダイレクトにpwm.begin
  Serial.print("pwm.begin() -> ");
  if (pwm.begin()) {
    Serial.println("OK!");
    pwm.setPWMFreq(50);
    Serial.println("PWM freq set to 50Hz");
  } else {
    Serial.println("FAILED");
  }
  
  // 2. フォールバック: 手動I2Cで生チェック
  Serial.print("Manual I2C check 0x70 -> ");
  Wire.begin();
  Wire.beginTransmission(0x70);
  if (Wire.endTransmission() == 0) {
    Serial.println("ACK!");
  } else {
    Serial.println("NO ACK");
  }
}

void loop() {}
