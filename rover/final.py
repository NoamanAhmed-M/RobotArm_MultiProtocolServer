#!/usr/bin/env python3
import Jetson.GPIO as GPIO
import time

# === Pin Definitions ===
IN1 = 7
IN2 = 11
ENA = 13
IN3 = 27
IN4 = 16
ENB = 18

# === PWM Balance Tuning ===
PWM_LEFT_RATIO = 0.32
PWM_RIGHT_RATIO = 1.0

# === GPIO Setup ===
GPIO.setmode(GPIO.BCM)
for pin in [IN1, IN2, ENA, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# === Motor Direction Functions ===
def set_motor_direction_forward():
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)

def set_motor_direction_backward():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)

def set_motor_direction_turn_right():
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)

def set_motor_direction_turn_left():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)

def stop_all():
    for pin in [IN1, IN2, IN3, IN4, ENA, ENB]:
        GPIO.output(pin, GPIO.LOW)

# === Motor Control using ON/OFF instead of time ===
def move(enable=1, direction="forward", speed=1.0):
    pwm_left = GPIO.PWM(ENA, 100)
    pwm_right = GPIO.PWM(ENB, 100)
    pwm_left.start(0)
    pwm_right.start(0)

    try:
        if enable == 1:
            if direction == "forward":
                set_motor_direction_forward()
            elif direction == "backward":
                set_motor_direction_backward()
            elif direction == "left":
                set_motor_direction_turn_left()
            elif direction == "right":
                set_motor_direction_turn_right()
            else:
                stop_all()
                return

            pwm_left.ChangeDutyCycle(speed * 100 * PWM_LEFT_RATIO)
            pwm_right.ChangeDutyCycle(speed * 100 * PWM_RIGHT_RATIO)
        else:
            stop_all()
            pwm_left.ChangeDutyCycle(0)
            pwm_right.ChangeDutyCycle(0)
    except KeyboardInterrupt:
        stop_all()
    finally:
        pwm_left.stop()
        pwm_right.stop()

# === Main Usage Example ===
if __name__ == "__main__":
    try:
        print("Move forward for 2 seconds...")
        move(1, direction="forward", speed=0.8)
        time.sleep(2)
        move(0)

        print("Turn left for 1 second...")
        move(1, direction="left", speed=0.7)
        time.sleep(1)
        move(0)

    except KeyboardInterrupt:
        print("\n[Interrupted by user]")
    finally:
        stop_all()
        GPIO.cleanup()
        print("GPIO cleanup done.")
