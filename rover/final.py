#!/usr/bin/env python3

import Jetson.GPIO as GPIO
import time

# ==== Pin Definitions (BCM Mode) ====
# Motor A
IN1 = 9    # Pin 21
IN2 = 10   # Pin 22
ENA = 18   # Pin 32

# Motor B
IN3 = 11   # Pin 23
IN4 = 8    # Pin 24
ENB = 19   # Pin 33

# ==== Setup ====
GPIO.setmode(GPIO.BCM)

for pin in [IN1, IN2, ENA, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)

# Setup software PWM at 1kHz for ENA and ENB
pwm_A = GPIO.PWM(ENA, 1000)
pwm_B = GPIO.PWM(ENB, 1000)
pwm_A.start(0)  # Start with 0% duty cycle (stopped)
pwm_B.start(0)

# ==== Motor Control Functions ====
def motor_a_forward(speed):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    pwm_A.ChangeDutyCycle(speed)

def motor_a_backward(speed):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    pwm_A.ChangeDutyCycle(speed)

def motor_b_forward(speed):
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_B.ChangeDutyCycle(speed)

def motor_b_backward(speed):
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    pwm_B.ChangeDutyCycle(speed)

def stop_all():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    pwm_A.ChangeDutyCycle(0)
    pwm_B.ChangeDutyCycle(0)

# ==== Main Program ====
try:
    print("Motor A forward (75%), Motor B backward (50%)")
    motor_a_forward(75)
    motor_b_backward(50)
    time.sleep(3)

    print("Reverse directions")
    motor_a_backward(60)
    motor_b_forward(100)
    time.sleep(3)

    print("Stop all motors")
    stop_all()
    time.sleep(2)

finally:
    pwm_A.stop()
    pwm_B.stop()
    GPIO.cleanup()
    print("GPIO cleanup complete.")
