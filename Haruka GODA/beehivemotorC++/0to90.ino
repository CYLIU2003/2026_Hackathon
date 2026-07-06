#include <Servo.h>

Servo servo;

const int buttonPin = 2; // ボタンを繋ぐデジタル2番ピン
const int servoPin = 3;  // サーボを繋ぐデジタル3番ピン

int motorState = 0;      // 0: 0度にある状態, 1: 90度にある状態
int lastButtonState = HIGH; 
int buttonState = HIGH; 
unsigned long lastDebounceTime = 0;  
unsigned long debounceDelay = 50;    // チャタリング防止タイマー（50ミリ秒）

void setup() {
  Serial.begin(9600);
  
  // 内部プルアップを有効にすることで、スイッチをシンプルにGNDに繋ぐだけで動作します
  pinMode(buttonPin, INPUT_PULLUP); 
  
  servo.attach(servoPin);
  servo.write(0); // 初期位置（0度）に移動
  
  Serial.println("--- Button Control Ready ---");
}

void loop() {
  int reading = digitalRead(buttonPin);

  // チャタリング（ノイズ）の排除ロジック
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading != buttonState) {
      buttonState = reading;

      // ボタンが押された瞬間（HIGHからLOWに変わった瞬間）だけを検知
      if (buttonState == LOW) {
        if (motorState == 0) {
          Serial.println("Button Pressed: Moving to 90 degrees...");
          
          // 0度から90度へゆっくり動かす（10度ずつ滑らかに変化）
          for (int angle = 0; angle <= 90; angle += 10) {
            servo.write(angle);
            delay(30);
          }
          motorState = 1; // 状態を「90度」に更新
        } 
        else if (motorState == 1) {
          Serial.println("Button Pressed: Moving to 0 degrees...");
          
          // 90度から0度へゆっくり戻す
          for (int angle = 90; angle >= 0; angle -= 10) {
            servo.write(angle);
            delay(30);
          }
          motorState = 0; // 状態を「0度」に更新
        }
      }
    }
  }

  lastButtonState = reading;
}