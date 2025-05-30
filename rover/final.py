#!/usr/bin/env python3

import Jetson.GPIO as GPIO
import time

# === Pin Definitions ===
# Motor A
IN1 = 9    # Pin 21
IN2 = 10   # Pin 22
ENA = 18   # Pin 32

# Motor B
IN3 = 11   # Pin 23
IN4 = 8    # Pin 24
ENB = 19   # Pin 33

# === Setup ===
GPIO.setmode(GPIO.BCM)

for pin in [IN1, IN2, ENA, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# === Software PWM Function ===
def software_pwm(pin, duty_cycle, frequency, duration):
    period = 1.0 / frequency
    on_time = period * duty_cycle
    off_time = period * (1 - duty_cycle)
    end_time = time.time() + duration

    while time.time() < end_time:
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(on_time)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(off_time)

# === Motor Functions ===
def motor_a_forward(speed, duration):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    software_pwm(ENA, speed, 100, duration)

def motor_a_backward(speed, duration):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    software_pwm(ENA, speed, 100, duration)

def motor_b_forward(speed, duration):
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    software_pwm(ENB, speed, 100, duration)

def motor_b_backward(speed, duration):
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    software_pwm(ENB, speed, 100, duration)

def stop_all():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    GPIO.output(ENA, GPIO.LOW)
    GPIO.output(ENB, GPIO.LOW)

# === Main Logic ===
try:
    print("Motor A Forward (75%), Motor B Backward (50%)")
    motor_a_forward(0.75, 3)     # 75% speed, 3 sec
    motor_b_backward(0.50, 3)    # 50% speed, 3 sec

    print("Reverse Directions")
    motor_a_backward(1.0, 2)
    motor_b_forward(0.3, 2)

    print("Stop all motors")
    stop_all()
    time.sleep(2)

finally:
    stop_all()
    GPIO.cleanup()
    print("GPIO cleanup complete.")
