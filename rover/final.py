#!/usr/bin/env python3
import Jetson.GPIO as GPIO
import time

# === Use BCM mode ===
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# === Pin Definitions ===
IN1 = 4     # GPIO4
IN2 = 17    # GPIO17
IN3 = 27    # GPIO27
IN4 = 22    # GPIO22
ENA = 13    # GPIO13 (PWM-capable)
ENB = 12    # GPIO12 (PWM-capable)

# === Setup all pins as outputs ===
for pin in [IN1, IN2, IN3, IN4, ENA, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# === Initialize PWM ===
pwm_left = GPIO.PWM(ENA, 100)  # 100 Hz
pwm_right = GPIO.PWM(ENB, 100)

pwm_left.start(0)
pwm_right.start(0)

# === Motor Control Functions ===
def stop():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    pwm_left.ChangeDutyCycle(0)
    pwm_right.ChangeDutyCycle(0)

def forward(speed=70):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    pwm_left.ChangeDutyCycle(speed)
    pwm_right.ChangeDutyCycle(speed)

def backward(speed=70):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_left.ChangeDutyCycle(speed)
    pwm_right.ChangeDutyCycle(speed)

def turn_left(speed=70):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    pwm_left.ChangeDutyCycle(speed)
    pwm_right.ChangeDutyCycle(speed)

def turn_right(speed=70):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_left.ChangeDutyCycle(speed)
    pwm_right.ChangeDutyCycle(speed)

# === Test ===
if __name__ == "__main__":
    try:
        print("Moving forward")
        forward(75)
        time.sleep(2)

        print("Turning left")
        turn_left(75)
        time.sleep(2)

        print("Moving backward")
        backward(60)
        time.sleep(2)

        print("Turning right")
        turn_right(75)
        time.sleep(2)

        print("Stopping")
        stop()
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        stop()
        pwm_left.stop()
        pwm_right.stop()
        GPIO.cleanup()
