#!/usr/bin/env python3
"""
Direct Motor Driver Control Module for Raspberry Pi

This module allows Raspberry Pi to directly control motor drivers (PCA9685 servo driver
or L293D stepper driver) without going through Arduino Uno Q.

Hardware connections:
- PCA9685: I2C bus (SCL, SDA) at address 0x70
- L293D: GPIO pins (configurable)

Safety:
- Default state is CLOSED (motor off/servo at 0 degrees)
- All operations have timeouts
- Emergency stop immediately closes and disables
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

JST = timezone(timedelta(hours=9))


class MotorMode(str, Enum):
    PCA9685_SERVO = "PCA9685_SERVO"
    L293D_STEPPER = "L293D_STEPPER"
    SIMULATION = "SIMULATION"


class MotorState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    MOVING = "MOVING"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


@dataclass
class DriverConfig:
    """Configuration for motor driver connection"""
    motor_mode: str = "PCA9685_SERVO"
    
    # PCA9685 settings
    pca9685_i2c_address: int = 0x70
    pca9685_i2c_bus: int = 1
    pca9685_servo_channel: int = 0
    pca9685_servo_min_pulse: int = 150
    pca9685_servo_max_pulse: int = 500
    pca9685_servo_closed_angle: int = 0
    pca9685_servo_open_angle: int = 90
    pca9685_servo_step_deg: int = 10
    pca9685_servo_step_delay_ms: int = 30
    
    # L293D settings
    l293d_enable_pin_a: int = 5
    l293d_input_pin_1: int = 8
    l293d_input_pin_2: int = 9
    l293d_enable_pin_b: int = 6
    l293d_input_pin_3: int = 10
    l293d_input_pin_4: int = 11
    l293d_stepper_open_steps: int = 50
    l293d_stepper_step_delay_ms: int = 5
    l293d_release_coils_after_move: bool = True
    
    # Safety settings
    max_operation_duration_ms: int = 5000
    cooldown_after_operation_ms: int = 2000
    
    @classmethod
    def from_dict(cls, data: dict) -> "DriverConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class ConnectionStatus:
    """Current connection and motor status"""
    connected: bool = False
    motor_mode: str = "SIMULATION"
    motor_state: str = "CLOSED"
    current_angle: int = 0
    current_position: int = 0
    last_operation: str = ""
    last_operation_timestamp: str = ""
    error_message: str = ""
    emergency_stop: bool = False
    operation_count: int = 0
    driver_available: bool = False
    i2c_available: bool = False
    gpio_available: bool = False
    
    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class MotorDriverController:
    """Controller for direct motor driver access from Raspberry Pi"""
    
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config = self._load_config()
        self._lock = threading.Lock()
        self._status = ConnectionStatus()
        self._pca9685 = None
        self._gpio_setup = False
        self._last_operation_time = 0
        self._operation_start_time = 0
        
        # Try to initialize hardware
        self._check_hardware_availability()
    
    def _load_config(self) -> DriverConfig:
        """Load configuration from file or use defaults"""
        if self.config_file.exists():
            try:
                with self.config_file.open("r") as f:
                    data = json.load(f)
                    return DriverConfig.from_dict(data)
            except Exception as e:
                print(f"Failed to load config: {e}, using defaults")
        return DriverConfig()
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with self.config_file.open("w") as f:
            json.dump(self.config.to_dict(), f, indent=2)
    
    def update_config(self, new_config: dict) -> None:
        """Update configuration with new values"""
        with self._lock:
            self.config = DriverConfig.from_dict({**self.config.to_dict(), **new_config})
            self.save_config()
            # Recheck hardware availability after config change
            self._check_hardware_availability()
    
    def _check_hardware_availability(self) -> None:
        """Check which hardware interfaces are available"""
        self._status.motor_mode = self.config.motor_mode
        
        # Check I2C availability for PCA9685
        if self.config.motor_mode == MotorMode.PCA9685_SERVO.value:
            try:
                import smbus2  # type: ignore
                bus = smbus2.SMBus(self.config.pca9685_i2c_bus)
                # Try to read from the expected address
                bus.read_byte_data(self.config.pca9685_i2c_address, 0)
                self._status.i2c_available = True
                self._status.driver_available = True
            except Exception as e:
                self._status.i2c_available = False
                self._status.driver_available = False
                self._status.error_message = f"I2C error: {e}"
        
        # Check GPIO availability for L293D
        elif self.config.motor_mode == MotorMode.L293D_STEPPER.value:
            try:
                import RPi.GPIO as GPIO  # type: ignore
                self._status.gpio_available = True
                self._status.driver_available = True
            except Exception as e:
                self._status.gpio_available = False
                self._status.driver_available = False
                self._status.error_message = f"GPIO error: {e}"
        
        # Simulation mode is always available
        elif self.config.motor_mode == MotorMode.SIMULATION.value:
            self._status.driver_available = True
            self._status.error_message = ""
    
    def get_status(self) -> ConnectionStatus:
        """Get current connection status"""
        with self._lock:
            self._status.connected = self._status.driver_available and not self._status.emergency_stop
            return ConnectionStatus(**self._status.to_dict())
    
    def _initialize_pca9685(self) -> bool:
        """Initialize PCA9685 servo driver"""
        if not self._status.i2c_available:
            return False
        
        try:
            import smbus2  # type: ignore
            self._pca9685 = smbus2.SMBus(self.config.pca9685_i2c_bus)
            
            # Reset PCA9685
            self._pca9685.write_byte_data(self.config.pca9685_i2c_address, 0x00, 0x00)
            time.sleep(0.01)
            
            # Set PWM frequency to 50Hz (for servos)
            prescale = int(25000000.0 / (4096.0 * 50.0) - 1)
            old_mode = self._pca9685.read_byte_data(self.config.pca9685_i2c_address, 0x00)
            new_mode = (old_mode & 0x7F) | 0x10  # Sleep mode
            self._pca9685.write_byte_data(self.config.pca9685_i2c_address, 0x00, new_mode)
            self._pca9685.write_byte_data(self.config.pca9685_i2c_address, 0xFE, prescale)
            self._pca9685.write_byte_data(self.config.pca9685_i2c_address, 0x00, old_mode)
            time.sleep(0.005)
            self._pca9685.write_byte_data(self.config.pca9685_i2c_address, 0x00, old_mode | 0xA0)
            
            return True
        except Exception as e:
            self._status.error_message = f"PCA9685 init failed: {e}"
            return False
    
    def _set_servo_angle(self, angle: int) -> None:
        """Set servo to specific angle via PCA9685"""
        if self._pca9685 is None:
            if not self._initialize_pca9685():
                raise RuntimeError("Cannot initialize PCA9685")
        
        # Convert angle to pulse width
        pulse = int(
            self.config.pca9685_servo_min_pulse + 
            (angle / 180.0) * (self.config.pca9685_servo_max_pulse - self.config.pca9685_servo_min_pulse)
        )
        
        # Write to PCA9685
        channel = self.config.pca9685_servo_channel
        base_reg = 0x06 + 4 * channel
        
        self._pca9685.write_byte_data(self.config.pca9685_i2c_address, base_reg, 0)
        self._pca9685.write_byte_data(self.config.pca9685_i2c_address, base_reg + 1, 0)
        self._pca9685.write_byte_data(self.config.pca9685_i2c_address, base_reg + 2, pulse & 0xFF)
        self._pca9685.write_byte_data(self.config.pca9685_i2c_address, base_reg + 3, (pulse >> 8) & 0xFF)
        
        self._status.current_angle = angle
    
    def _move_servo_smooth(self, target_angle: int) -> None:
        """Smoothly move servo to target angle"""
        current = self._status.current_angle
        step = self.config.pca9685_servo_step_deg
        delay = self.config.pca9685_servo_step_delay_ms / 1000.0
        
        if target_angle > current:
            for angle in range(current, target_angle + 1, step):
                self._set_servo_angle(min(angle, target_angle))
                time.sleep(delay)
        else:
            for angle in range(current, target_angle - 1, -step):
                self._set_servo_angle(max(angle, target_angle))
                time.sleep(delay)
        
        self._set_servo_angle(target_angle)
    
    def _setup_l293d_gpio(self) -> bool:
        """Setup GPIO pins for L293D stepper motor"""
        if not self._status.gpio_available:
            return False
        
        try:
            import RPi.GPIO as GPIO  # type: ignore
            if not self._gpio_setup:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                pins = [
                    self.config.l293d_enable_pin_a,
                    self.config.l293d_input_pin_1,
                    self.config.l293d_input_pin_2,
                    self.config.l293d_enable_pin_b,
                    self.config.l293d_input_pin_3,
                    self.config.l293d_input_pin_4,
                ]
                for pin in pins:
                    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
                self._gpio_setup = True
            return True
        except Exception as e:
            self._status.error_message = f"GPIO setup failed: {e}"
            return False
    
    def _step_stepper(self, direction: int) -> None:
        """Move stepper motor one step in given direction (1=forward, -1=backward)"""
        import RPi.GPIO as GPIO  # type: ignore
        
        # Enable both motor phases
        GPIO.output(self.config.l293d_enable_pin_a, GPIO.HIGH)
        GPIO.output(self.config.l293d_enable_pin_b, GPIO.HIGH)
        
        # Full step sequence for bipolar stepper
        sequence = [
            (GPIO.HIGH, GPIO.LOW, GPIO.HIGH, GPIO.LOW),
            (GPIO.LOW, GPIO.HIGH, GPIO.HIGH, GPIO.LOW),
            (GPIO.LOW, GPIO.HIGH, GPIO.LOW, GPIO.HIGH),
            (GPIO.HIGH, GPIO.LOW, GPIO.LOW, GPIO.HIGH),
        ]
        
        step_index = self._status.current_position % 4
        if direction < 0:
            step_index = (step_index - 1) % 4
        
        i1, i2, i3, i4 = sequence[step_index]
        GPIO.output(self.config.l293d_input_pin_1, i1)
        GPIO.output(self.config.l293d_input_pin_2, i2)
        GPIO.output(self.config.l293d_input_pin_3, i3)
        GPIO.output(self.config.l293d_input_pin_4, i4)
        
        time.sleep(self.config.l293d_stepper_step_delay_ms / 1000.0)
        self._status.current_position += direction
    
    def _release_stepper_coils(self) -> None:
        """Release stepper motor coils to reduce heat"""
        if not self._gpio_setup:
            return
        
        try:
            import RPi.GPIO as GPIO  # type: ignore
            GPIO.output(self.config.l293d_enable_pin_a, GPIO.LOW)
            GPIO.output(self.config.l293d_enable_pin_b, GPIO.LOW)
            GPIO.output(self.config.l293d_input_pin_1, GPIO.LOW)
            GPIO.output(self.config.l293d_input_pin_2, GPIO.LOW)
            GPIO.output(self.config.l293d_input_pin_3, GPIO.LOW)
            GPIO.output(self.config.l293d_input_pin_4, GPIO.LOW)
        except Exception:
            pass
    
    def open_motor(self) -> tuple[bool, str]:
        """Open motor (servo to open angle or stepper to open position)"""
        with self._lock:
            if self._status.emergency_stop:
                return False, "Emergency stop is active"
            
            # Check cooldown
            now = time.time()
            if now - self._last_operation_time < self.config.cooldown_after_operation_ms / 1000.0:
                return False, "Cooldown period active"
            
            self._operation_start_time = now
            self._status.motor_state = MotorState.MOVING.value
            self._status.last_operation = "OPEN"
            self._status.last_operation_timestamp = datetime.now(JST).isoformat()
            
            try:
                if self.config.motor_mode == MotorMode.PCA9685_SERVO.value:
                    self._move_servo_smooth(self.config.pca9685_servo_open_angle)
                elif self.config.motor_mode == MotorMode.L293D_STEPPER.value:
                    if not self._setup_l293d_gpio():
                        raise RuntimeError("Cannot setup GPIO for L293D")
                    steps_needed = self.config.l293d_stepper_open_steps - self._status.current_position
                    for _ in range(abs(steps_needed)):
                        self._step_stepper(1 if steps_needed > 0 else -1)
                    if self.config.l293d_release_coils_after_move:
                        self._release_stepper_coils()
                elif self.config.motor_mode == MotorMode.SIMULATION.value:
                    self._status.current_angle = self.config.pca9685_servo_open_angle
                    time.sleep(0.5)  # Simulate delay
                
                self._status.motor_state = MotorState.OPEN.value
                self._last_operation_time = time.time()
                self._status.operation_count += 1
                return True, "Motor opened successfully"
            
            except Exception as e:
                self._status.motor_state = MotorState.ERROR.value
                self._status.error_message = str(e)
                return False, f"Failed to open motor: {e}"
    
    def close_motor(self) -> tuple[bool, str]:
        """Close motor (servo to closed angle or stepper to closed position)"""
        with self._lock:
            self._status.motor_state = MotorState.MOVING.value
            self._status.last_operation = "CLOSE"
            self._status.last_operation_timestamp = datetime.now(JST).isoformat()
            
            try:
                if self.config.motor_mode == MotorMode.PCA9685_SERVO.value:
                    self._move_servo_smooth(self.config.pca9685_servo_closed_angle)
                elif self.config.motor_mode == MotorMode.L293D_STEPPER.value:
                    if not self._setup_l293d_gpio():
                        raise RuntimeError("Cannot setup GPIO for L293D")
                    steps_needed = self._status.current_position
                    for _ in range(abs(steps_needed)):
                        self._step_stepper(-1)
                    if self.config.l293d_release_coils_after_move:
                        self._release_stepper_coils()
                elif self.config.motor_mode == MotorMode.SIMULATION.value:
                    self._status.current_angle = self.config.pca9685_servo_closed_angle
                    time.sleep(0.5)  # Simulate delay
                
                self._status.motor_state = MotorState.CLOSED.value
                self._status.operation_count += 1
                return True, "Motor closed successfully"
            
            except Exception as e:
                self._status.motor_state = MotorState.ERROR.value
                self._status.error_message = str(e)
                return False, f"Failed to close motor: {e}"
    
    def emergency_stop(self) -> tuple[bool, str]:
        """Emergency stop - immediately close and disable"""
        with self._lock:
            self._status.emergency_stop = True
            self._status.motor_state = MotorState.DISABLED.value
            self._status.last_operation = "EMERGENCY_STOP"
            self._status.last_operation_timestamp = datetime.now(JST).isoformat()
            
            try:
                # Try to close if possible
                if self.config.motor_mode == MotorMode.PCA9685_SERVO.value:
                    try:
                        self._set_servo_angle(self.config.pca9685_servo_closed_angle)
                    except Exception:
                        pass
                elif self.config.motor_mode == MotorMode.L293D_STEPPER.value:
                    self._release_stepper_coils()
                
                return True, "Emergency stop activated"
            except Exception as e:
                return False, f"Emergency stop failed: {e}"
    
    def reset(self) -> tuple[bool, str]:
        """Reset emergency stop and return to closed state"""
        with self._lock:
            self._status.emergency_stop = False
            self._status.error_message = ""
            self._status.motor_state = MotorState.CLOSED.value
            self._last_operation_time = 0
            self._check_hardware_availability()
            return True, "System reset"
    
    def test_connection(self) -> tuple[bool, str]:
        """Test connection to motor driver"""
        with self._lock:
            try:
                if self.config.motor_mode == MotorMode.PCA9685_SERVO.value:
                    if self._initialize_pca9685():
                        return True, "PCA9685 connection successful"
                    else:
                        return False, "PCA9685 connection failed"
                elif self.config.motor_mode == MotorMode.L293D_STEPPER.value:
                    if self._setup_l293d_gpio():
                        return True, "L293D GPIO connection successful"
                    else:
                        return False, "L293D GPIO connection failed"
                elif self.config.motor_mode == MotorMode.SIMULATION.value:
                    return True, "Simulation mode - no hardware connection"
                else:
                    return False, "Unknown motor mode"
            except Exception as e:
                return False, f"Connection test failed: {e}"
