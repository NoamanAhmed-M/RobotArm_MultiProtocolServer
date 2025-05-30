#!/usr/bin/env python3

import Jetson.GPIO as GPIO
import time

# BCM GPIO numbers
ENA = 18   # Pin 32
IN1 = 25   # Pin 22
IN2 = 27   # Pin 13

GPIO.setmode(GPIO.BCM)

# Setup GPIO pins
GPIO.setup(ENA, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(IN1, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(IN2, GPIO.OUT, initial=GPIO.LOW)

try:
    print("Motor STOP")
    GPIO.output(ENA, GPIO.HIGH)
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    time.sleep(1)

    print("Motor FORWARD")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    time.sleep(1)

    print("Motor STOP")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    time.sleep(1)

    print("Motor BACKWARD")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    time.sleep(1)

    print("Final STOP")
    GPIO.output(ENA, GPIO.LOW)
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    time.sleep(1)

finally:
    GPIO.cleanup()
