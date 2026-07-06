#include <SPI.h>
#include <AD9833.h>
#include <math.h>

//==================================================
// AD9833
//==================================================
#define DDS1_CS 5
#define DDS2_CS 17

AD9833 dds1(DDS1_CS);
AD9833 dds2(DDS2_CS);

//==================================================
// Frequency
//==================================================
const float FREQ1 = 5000.0;      // Measurement DDS
const float FREQ2 = 5100.0;      // Reference DDS
const float BEAT  = 100.0;       // Beat frequency

//==================================================
// ADC
//==================================================
const int ADC1_PIN = 34;
const int ADC2_PIN = 35;

//==================================================
// Arduino Uno UART Link
//==================================================
const int BIA_UART_TX_PIN = 16;
const int BIA_UART_BAUDRATE = 9600;
const unsigned long USB_OUTPUT_INTERVAL_MS = 100;
const unsigned long UART_OUTPUT_INTERVAL_MS = 250;

//==================================================
// Sampling
//==================================================
const int SAMPLE_NUM = 40;
const float SAMPLE_INTERVAL_US = 250.0;
const float SAMPLE_RATE = 4000.0;

//==================================================
// Sample Buffers
//==================================================
float sample1[SAMPLE_NUM];
float sample2[SAMPLE_NUM];

//==================================================
// Reference LUT
//==================================================
float refCos[SAMPLE_NUM];
float refSin[SAMPLE_NUM];

//==================================================
// Results
//==================================================
float I1, Q1, amplitude1, phase1;
float I2, Q2, amplitude2, phase2;

//==================================================
// Contact Decision
//==================================================
const float DEFAULT_CONTACT_AMPLITUDE_THRESHOLD = 30.0f;
const float CALIBRATION_CONTACT_MARGIN = 20.0f;
const int CALIBRATION_SAMPLE_COUNT = 50;

float manualContactThreshold = DEFAULT_CONTACT_AMPLITUDE_THRESHOLD;
float baselineAmplitude1 = 0.0f;
bool calibrationReady = false;
bool calibrationActive = false;
int calibrationSamplesRemaining = 0;
float calibrationAmplitudeSum = 0.0f;

const int SERIAL_COMMAND_BUFFER_SIZE = 40;
char serialCommandBuffer[SERIAL_COMMAND_BUFFER_SIZE];
int serialCommandLength = 0;
unsigned long lastUsbOutputMs = 0;
unsigned long lastUartOutputMs = 0;

//==================================================
// IQ Detection Function
//==================================================
void IQdetect(float sample[],
              float &I,
              float &Q,
              float &amplitude,
              float &phaseDeg)
{
    //------------------------
    // Remove DC Offset
    //------------------------
    float offset = 0;

    for (int i = 0; i < SAMPLE_NUM; i++)
        offset += sample[i];

    offset /= SAMPLE_NUM;

    for (int i = 0; i < SAMPLE_NUM; i++)
        sample[i] -= offset;

    //------------------------
    // IQ Detection
    //------------------------
    I = 0;
    Q = 0;

    for (int i = 0; i < SAMPLE_NUM; i++)
    {
        I += sample[i] * refCos[i];
        Q += sample[i] * refSin[i];
    }

    I /= SAMPLE_NUM;
    Q /= SAMPLE_NUM;

    //------------------------
    // Amplitude
    //------------------------
    amplitude = 2.0 * sqrt(I * I + Q * Q);

    //------------------------
    // Phase
    //------------------------
    phaseDeg = atan2(Q, I) * 180.0 / PI;
}

//==================================================
// Contact / Command Helpers
//==================================================
float activeContactThreshold()
{
    if (calibrationReady)
        return baselineAmplitude1 + CALIBRATION_CONTACT_MARGIN;

    return manualContactThreshold;
}

bool contactDetected()
{
    return amplitude1 >= activeContactThreshold();
}

void printBool(Print &output, bool value)
{
    output.print(value ? F("true") : F("false"));
}

void emitBiaJsonLine(Print &output)
{
    output.print(F("{\"timestamp\":\"T+"));
    output.print(millis());
    output.print(F("ms\",\"source\":\"esp32_bia\",\"contact_detected\":"));
    printBool(output, contactDetected());
    output.print(F(",\"amplitude1\":"));
    output.print(amplitude1, 3);
    output.print(F(",\"phase1\":"));
    output.print(phase1, 3);
    output.print(F(",\"amplitude2\":"));
    output.print(amplitude2, 3);
    output.print(F(",\"phase2\":"));
    output.print(phase2, 3);
    output.print(F(",\"contact_threshold\":"));
    output.print(activeContactThreshold(), 3);
    output.print(F(",\"calibrated\":"));
    printBool(output, calibrationReady);
    output.print(F("}"));
    output.println();
}

void emitBiaUnoJsonLine(Print &output)
{
    output.print(F("{\"contact_detected\":"));
    printBool(output, contactDetected());
    output.print(F(",\"amplitude1\":"));
    output.print(amplitude1, 3);
    output.print(F(",\"phase1\":"));
    output.print(phase1, 3);
    output.print(F(",\"amplitude2\":"));
    output.print(amplitude2, 3);
    output.print(F(",\"phase2\":"));
    output.print(phase2, 3);
    output.print(F("}"));
    output.println();
}

void emitEventJsonLine(const __FlashStringHelper *eventName)
{
    Serial.print(F("{\"timestamp\":\"T+"));
    Serial.print(millis());
    Serial.print(F("ms\",\"source\":\"esp32_bia\",\"event\":\""));
    Serial.print(eventName);
    Serial.println(F("\"}"));
}

void startCalibration()
{
    calibrationActive = true;
    calibrationReady = false;
    calibrationSamplesRemaining = CALIBRATION_SAMPLE_COUNT;
    calibrationAmplitudeSum = 0.0f;
    emitEventJsonLine(F("BIA_CALIBRATION_START"));
}

void updateCalibration()
{
    if (!calibrationActive)
        return;

    calibrationAmplitudeSum += amplitude1;
    calibrationSamplesRemaining--;

    if (calibrationSamplesRemaining <= 0)
    {
        baselineAmplitude1 = calibrationAmplitudeSum / CALIBRATION_SAMPLE_COUNT;
        calibrationReady = true;
        calibrationActive = false;
        emitEventJsonLine(F("BIA_CALIBRATION_DONE"));
    }
}

void clearSerialCommandBuffer()
{
    serialCommandLength = 0;
    serialCommandBuffer[0] = '\0';
}

void handleSerialCommand(char *command)
{
    while (*command == ' ')
        command++;

    if (strcmp(command, "CALIBRATE") == 0)
    {
        startCalibration();
        return;
    }

    if (strncmp(command, "SET_THRESHOLD ", 14) == 0)
    {
        float nextThreshold = atof(command + 14);
        if (nextThreshold > 0.0f)
        {
            manualContactThreshold = nextThreshold;
            calibrationReady = false;
            emitEventJsonLine(F("BIA_THRESHOLD_SET"));
        }
        else
        {
            emitEventJsonLine(F("BIA_BAD_THRESHOLD"));
        }
        return;
    }

    if (strcmp(command, "STATUS") == 0)
    {
        emitBiaJsonLine(Serial);
        return;
    }

    emitEventJsonLine(F("BIA_UNKNOWN_COMMAND"));
}

void processSerialCommands()
{
    while (Serial.available() > 0)
    {
        char incoming = static_cast<char>(Serial.read());

        if (incoming == '\r')
            continue;

        if (incoming == '\n')
        {
            if (serialCommandLength > 0)
            {
                serialCommandBuffer[serialCommandLength] = '\0';
                handleSerialCommand(serialCommandBuffer);
                clearSerialCommandBuffer();
            }
            continue;
        }

        if (serialCommandLength < SERIAL_COMMAND_BUFFER_SIZE - 1)
        {
            serialCommandBuffer[serialCommandLength++] = incoming;
        }
    }
}

//==================================================
// Setup
//==================================================
void setup()
{
    Serial.begin(115200);
    Serial2.begin(BIA_UART_BAUDRATE, SERIAL_8N1, -1, BIA_UART_TX_PIN);
    clearSerialCommandBuffer();

    //------------------------
    // SPI
    //------------------------
    SPI.begin(18, -1, 23, -1);

    //------------------------
    // DDS
    //------------------------
    dds1.begin();
    dds2.begin();

    dds1.setWave(AD9833_SINE);
    dds2.setWave(AD9833_SINE);

    dds1.setFrequency(FREQ1);
    dds2.setFrequency(FREQ2);

    dds1.setPhase(0);
    dds2.setPhase(0);

    //------------------------
    // ADC
    //------------------------
    analogReadResolution(12);

    //------------------------
    // Reference Table
    //------------------------
    for (int i = 0; i < SAMPLE_NUM; i++)
    {
        float t = (float)i / SAMPLE_RATE;

        refCos[i] = cosf(2.0f * PI * BEAT * t);
        refSin[i] = sinf(2.0f * PI * BEAT * t);
    }

    delay(1000);

    emitEventJsonLine(F("BIA_START"));
}

//==================================================
// Loop
//==================================================
void loop()
{
    unsigned long now = millis();
    processSerialCommands();

    //------------------------
    // Sampling
    //------------------------
    uint32_t start = micros();

    for (int i = 0; i < SAMPLE_NUM; i++)
    {
        while (micros() - start < (uint32_t)(i * SAMPLE_INTERVAL_US));

        sample1[i] = analogRead(ADC1_PIN);
        sample2[i] = analogRead(ADC2_PIN);
    }

    //------------------------
    // IQ Detection
    //------------------------
    IQdetect(sample1, I1, Q1, amplitude1, phase1);
    IQdetect(sample2, I2, Q2, amplitude2, phase2);
    updateCalibration();

    //------------------------
    // JSON Lines output
    //------------------------
    if (now - lastUsbOutputMs >= USB_OUTPUT_INTERVAL_MS)
    {
        lastUsbOutputMs = now;
        emitBiaJsonLine(Serial);
    }

    if (now - lastUartOutputMs >= UART_OUTPUT_INTERVAL_MS)
    {
        lastUartOutputMs = now;
        emitBiaUnoJsonLine(Serial2);
    }

    delay(10);
}
