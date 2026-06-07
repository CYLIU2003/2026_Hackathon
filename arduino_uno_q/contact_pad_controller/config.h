#pragma once

const int PIN_RELEASE_LED = 13;
const int PIN_RELEASE_SIGNAL = 8;
const int PIN_EMERGENCY_STOP = 7;
const int PIN_SIM_BEAR_INPUT = 2;
const int PIN_SIM_CONTACT_INPUT = 3;
const int PIN_CONTACT_ANALOG = A0;
const int PIN_HONEY_ANALOG = A1;
const int PIN_STATUS_LED = 12;

const int HONEY_MIN_THRESHOLD_PERCENT = 20;
const unsigned long CONTACT_CONFIRM_DURATION_MS = 500;
const unsigned long MAX_RELEASE_DURATION_MS = 3000;
const unsigned long COOLDOWN_AFTER_RELEASE_MS = 5000;
const unsigned long MESSAGE_INTERVAL_MS = 1000;
const unsigned long SENSOR_UPDATE_INTERVAL_MS = 100;
const int SERIAL_BAUDRATE = 115200;

const int DEFAULT_HONEY_AMOUNT_PERCENT = 80;
