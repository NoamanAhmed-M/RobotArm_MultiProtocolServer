#!/usr/bin/env python3

import Jetson.GPIO as GPIO
import time

# BCM Pins
ENA = 19   # Pin 33 - software PWM output
IN1 = 25   # Pin 22
IN2 = 27   # Pin 13

GPIO.setmode(GPIO.BCM)
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)

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

try:
    print("FORWARD at 75% speed (software PWM)")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    software_pwm(ENA, duty_cycle=0.75, frequency=100, duration=2)

    print("STOP")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(ENA, GPIO.LOW)
    time.sleep(1)

    print("BACKWARD at 50% speed (software PWM)")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    software_pwm(ENA, duty_cycle=0.5, frequency=100, duration=2)

    print("STOP")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(ENA, GPIO.LOW)

finally:
    GPIO.cleanup()
