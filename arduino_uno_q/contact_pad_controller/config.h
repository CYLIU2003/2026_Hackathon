#pragma once

#include <Arduino.h>

const int PIN_RELEASE_LED = 13;
const int PIN_RELEASE_SIGNAL = 8;
const int PIN_EMERGENCY_STOP = 7;
const int PIN_SIM_BEAR_INPUT = 2;
const int PIN_SIM_CONTACT_INPUT = 3;
const int PIN_BIA_SERIAL_RX = 4;
const int PIN_BIA_SERIAL_TX_UNUSED = 5;
const int PIN_CONTACT_ANALOG = A0;
const int PIN_HONEY_ANALOG = A1;
const int PIN_STATUS_LED = 12;
const int PIN_GODA_DIRECT_SERVO = 3;

const int HONEY_MIN_THRESHOLD_PERCENT = 20;
const unsigned long CONTACT_CONFIRM_DURATION_MS = 500;
const unsigned long MAX_RELEASE_DURATION_MS = 3000;
const unsigned long COOLDOWN_AFTER_RELEASE_MS = 5000;
const unsigned long MESSAGE_INTERVAL_MS = 1000;
const unsigned long SENSOR_UPDATE_INTERVAL_MS = 100;
const int SERIAL_BAUDRATE = 115200;

#define BIA_INPUT_ENABLED 0
#define BIA_USE_HARDWARE_SERIAL1 0
const int BIA_SERIAL_BAUDRATE = 9600;
const unsigned long BIA_INPUT_TIMEOUT_MS = 1500;
const int BIA_MESSAGE_BUFFER_SIZE = 220;

const int DEFAULT_HONEY_AMOUNT_PERCENT = 80;

#define GODA_ACTUATOR_MODE_PCA9685 1
#define GODA_ACTUATOR_MODE_DIRECT_SERVO 2

// Haruka GODA/beehivemotorC++/0to90/0to90.ino uses a direct Servo.h motor on D3.
// Change this to GODA_ACTUATOR_MODE_PCA9685 if the venue wiring uses PCA9685.
#ifndef GODA_ACTUATOR_MODE
#define GODA_ACTUATOR_MODE GODA_ACTUATOR_MODE_DIRECT_SERVO
#endif

const uint8_t GODA_PCA9685_I2C_ADDRESS = 0x40;
const uint8_t GODA_SERVO_CHANNEL = 0;
const int GODA_SERVO_MIN_PULSE = 150;
const int GODA_SERVO_MAX_PULSE = 500;
const int GODA_SERVO_CLOSED_ANGLE = 0;
const int GODA_SERVO_OPEN_ANGLE = 90;
const int GODA_SERVO_STEP_DEG = 5;
const int GODA_SERVO_STEP_DELAY_MS = 15;
