#include <Wire.h>

void setup() {
  Serial.begin(115200);
  Wire.begin();
}

void loop() {
  static unsigned long lastScan = 0;
  if (millis() - lastScan > 1000) {
    lastScan = millis();
    int found = 0;
    for (int addr = 1; addr < 128; addr++) {
      Wire.beginTransmission(addr);
      if (Wire.endTransmission() == 0) {
        Serial.print("FOUND 0x");
        Serial.print(addr, HEX);
        Serial.print(" | ");
        found++;
      }
    }
    if (found == 0) {
      Serial.print("NO DEVICE");
    }
    Serial.println();
  }
}
