#include <Wire.h>

void setup() {
  Serial.begin(9600);
  Wire.begin();
  Serial.println("=== I2C Scanner ===");
  
  int found = 0;
  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    byte error = Wire.endTransmission();
    
    if (error == 0) {
      Serial.print("Found device at 0x");
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
    Serial.println("No I2C devices found! Check wiring.");
    Serial.println("SDA=A4, SCL=A5 (Uno)");
  } else {
    Serial.print("Total: ");
    Serial.print(found);
    Serial.println(" device(s) found.");
  }
}

void loop() {}
