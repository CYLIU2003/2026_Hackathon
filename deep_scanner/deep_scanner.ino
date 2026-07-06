#include <Wire.h>

void setup() {
  Serial.begin(9600);
  Wire.begin();
  Serial.println("=== Deep I2C Scanner ===");
  Serial.print("SDA pin: A4, SCL pin: A5\n");
  
  // SDA, SCL の電圧状態を確認（digitalRead）
  pinMode(A4, INPUT_PULLUP);
  pinMode(A5, INPUT_PULLUP);
  Serial.print("SDA (A4) RAW: "); Serial.println(digitalRead(A4));
  Serial.print("SCL (A5) RAW: "); Serial.println(digitalRead(A5));
  
  // Wireライブラリ再初期化
  Wire.begin();
  
  // 全アドレス (1-127) をスキャン
  Serial.println("--- Scanning ALL addresses (1-127) ---");
  int found = 0;
  for (int addr = 1; addr < 128; addr++) {
    Wire.beginTransmission(addr);
    byte error = Wire.endTransmission();
    if (error == 0) {
      Serial.print("FOUND: 0x");
      if (addr < 16) Serial.print("0");
      Serial.print(addr, HEX);
      Serial.print(" (");
      Serial.print(addr);
      Serial.println(")");
      found++;
    }
    delay(2);
  }
  
  if (found == 0) {
    Serial.println("=== NO DEVICES FOUND ===");
    Serial.println("Possible causes:");
    Serial.println("1. SDA/SCL wiring (A4->SDA, A5->SCL)");
    Serial.println("2. PCA9685 VCC must be 5V");
    Serial.println("3. PCA9685 GND must be connected");
    Serial.println("4. Try swap SDA/SCL (some boards label wrong)");
    Serial.println("5. No pull-up resistors (rare)");
  } else {
    Serial.print("=== Total: ");
    Serial.print(found);
    Serial.println(" device(s) ===");
  }
  
  // ボタンテスト
  pinMode(2, INPUT_PULLUP);
  pinMode(13, OUTPUT);
  Serial.println("=== Button Test (pin 2) ===");
  Serial.println("Press button to see message...");
}

void loop() {
  static int lastBtn = HIGH;
  int btn = digitalRead(2);
  if (btn != lastBtn) {
    lastBtn = btn;
    Serial.print("Button: ");
    Serial.println(btn == LOW ? "PRESSED" : "RELEASED");
    digitalWrite(13, btn == LOW ? HIGH : LOW);
  }
  delay(10);
}
