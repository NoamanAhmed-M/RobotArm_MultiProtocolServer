#!/usr/bin/env python3

import Jetson.GPIO as GPIO
import time

# === Pin Definitions ===
# Motor A
IN1 = 7    # Pin 21
IN2 = 11   # Pin 22
ENA = 13   # Pin 32

# Motor B
IN3 = 27   # Pin 23
IN4 = 16   # Pin 24
ENB = 18   # Pin 33

# === GPIO Setup ===
GPIO.setmode(GPIO.BCM)

for pin in [IN1, IN2, ENA, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# === Custom Dual PWM Function ===
def synchronized_pwm(pin_a, pin_b, duty_a, duty_b, frequency, duration):
    period = 1.0 / frequency
    on_time_a = period * duty_a
    on_time_b = period * duty_b
    end_time = time.time() + duration

    while time.time() < end_time:
        # Turn on both motors according to their respective duty cycles
        if duty_a > 0:
            GPIO.output(pin_a, GPIO.HIGH)
        if duty_b > 0:
            GPIO.output(pin_b, GPIO.HIGH)
        
        # Run for the minimum on-time
        time.sleep(min(on_time_a, on_time_b))

        # Turn off individual motors if needed
        if on_time_a <= on_time_b:
            GPIO.output(pin_a, GPIO.LOW)
            time.sleep(on_time_b - on_time_a)
            GPIO.output(pin_b, GPIO.LOW)
        else:
            GPIO.output(pin_b, GPIO.LOW)
            time.sleep(on_time_a - on_time_b)
            GPIO.output(pin_a, GPIO.LOW)

        # Wait for off period
        off_time = period - max(on_time_a, on_time_b)
        if off_time > 0:
            time.sleep(off_time)

# === Motor Movement Functions ===
def motors_forward(speed_a, speed_b, duration):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    synchronized_pwm(ENA, ENB, speed_a, speed_b, 100, duration)

def motors_backward(speed_a, speed_b, duration):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    synchronized_pwm(ENA, ENB, speed_a, speed_b, 100, duration)


def stop_all():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    GPIO.output(ENA, GPIO.LOW)
    GPIO.output(ENB, GPIO.LOW)

# === Main Execution ===
try:
    print("Moving forward...")
    motors_forward(0.4, 1, 3)  # Adjust speed here if one motor is faster
    print("Forward movement complete.")

    time.sleep(1)

    print("Moving backward...")
    motors_backward(0.4, 1, 3)  # Same adjustment for backward
    print("Backward movement complete.")

    stop_all()
    time.sleep(2)

finally:
    stop_all()
    GPIO.cleanup()
    print("GPIO cleanup complete.")
