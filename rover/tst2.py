#!/usr/bin/env python3

import Jetson.GPIO as GPIO
import time

# Pin mappings (BCM)
ENA = 19   # Pin 33 — we'll use software PWM here
IN1 = 25   # Pin 22
IN2 = 27   # Pin 13

GPIO.setmode(GPIO.BCM)

# Set up pins
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)

# Set up software PWM at 1kHz
pwm = GPIO.PWM(ENA, 1000)
pwm.start(0)  # Start with motor off

try:
    print("FORWARD at 75% speed")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    pwm.ChangeDutyCycle(75)
    time.sleep(2)

    print("STOP")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    pwm.ChangeDutyCycle(0)
    time.sleep(1)

    print("BACKWARD at 50% speed")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    pwm.ChangeDutyCycle(50)
    time.sleep(2)

    print("STOP")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    pwm.ChangeDutyCycle(0)
    time.sleep(1)

finally:
    print("Cleaning up...")
    pwm.stop()
    GPIO.cleanup()
