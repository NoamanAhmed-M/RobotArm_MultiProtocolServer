#!/usr/bin/env python3
import Jetson.GPIO as GPIO
import time

# === Pin Definitions ===
IN1 = 4    # Grigio -> Pin 7 (GPIO4)
IN2 = 17   # Giallo -> Pin 11 (GPIO17)
ENA = 13   # Viola -> Pin 33 (GPIO13)

IN3 = 27   # Blu -> Pin 13 (GPIO27)
IN4 = 22   # Verde -> Pin 15 (GPIO22)
ENB = 12   # Bianco -> Pin 32 (GPIO12)

# === GPIO Setup ===
GPIO.setmode(GPIO.BCM)
for pin in [IN1, IN2, IN3, IN4, ENA, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# === PWM Setup ===
pwmA = GPIO.PWM(ENA, 100)  # Left motor (Motor A)
pwmB = GPIO.PWM(ENB, 100)  # Right motor (Motor B)
pwmA.start(0)
pwmB.start(0)

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
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    pwmA.ChangeDutyCycle(0)
    pwmB.ChangeDutyCycle(0)

# === Movement Functions with Separate Speeds ===
def step_move(direction_fn, left_speed, right_speed, step_time=0.1):
    direction_fn()
    pwmA.ChangeDutyCycle(left_speed)
    pwmB.ChangeDutyCycle(right_speed)
    time.sleep(step_time)
    stop_all()

# === High-Level Step Movements ===
def move_forward_step(left_speed=70, right_speed=70, step_time=0.1):
    print(f"Forward: Left={left_speed}%, Right={right_speed}%")
    step_move(set_motor_direction_forward, left_speed, right_speed, step_time)

def move_backward_step(left_speed=70, right_speed=70, step_time=0.1):
    print(f"Backward: Left={left_speed}%, Right={right_speed}%")
    step_move(set_motor_direction_backward, left_speed, right_speed, step_time)

def turn_right_step(left_speed=70, right_speed=70, step_time=0.1):
    print(f"Turn Right: Left={left_speed}%, Right={right_speed}%")
    step_move(set_motor_direction_turn_right, left_speed, right_speed, step_time)

def turn_left_step(left_speed=70, right_speed=70, step_time=0.1):
    print(f"Turn Left: Left={left_speed}%, Right={right_speed}%")
    step_move(set_motor_direction_turn_left, left_speed, right_speed, step_time)

# === Demo ===
def demo_steps():
    move_forward_step(60, 70, 0.4)
    time.sleep(0.3)
    move_backward_step(70, 60, 0.4)
    time.sleep(0.3)
    turn_right_step(70, 70, 0.4)
    time.sleep(0.3)
    turn_left_step(70, 70, 0.4)

# === Main ===
if __name__ == "__main__":
    try:
        print("Jetson Nano - Step Motor Control with Per-Motor Speed")
        demo_steps()

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        stop_all()
        pwmA.stop()
        pwmB.stop()
        GPIO.cleanup()
        print("GPIO cleanup complete.")
