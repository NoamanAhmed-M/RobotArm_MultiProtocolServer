#!/usr/bin/env python3
import Jetson.GPIO as GPIO
import time

# === Pin Definitions ===
# Motor A
IN1 = 4    # Grigio -> Pin 7 (GPIO4)
IN2 = 17   # Giallo -> Pin 11 (GPIO17)
ENA = 13   # Viola -> Pin 33 (GPIO13)

# Motor B
IN3 = 27   # Blu -> Pin 13 (GPIO27)
IN4 = 22   # Verde -> Pin 15 (GPIO22)
ENB = 12   # Bianco -> Pin 32 (GPIO12)

# === GPIO Setup ===
GPIO.setmode(GPIO.BCM)
for pin in [IN1, IN2, ENA, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# === Low-level Motor Control ===
def set_motor_direction_forward():
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    GPIO.output(ENA, GPIO.HIGH)
    GPIO.output(ENB, GPIO.HIGH)

def set_motor_direction_backward():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    GPIO.output(ENA, GPIO.HIGH)
    GPIO.output(ENB, GPIO.HIGH)

def set_motor_direction_turn_right():
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    GPIO.output(ENA, GPIO.HIGH)
    GPIO.output(ENB, GPIO.HIGH)

def set_motor_direction_turn_left():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    GPIO.output(ENA, GPIO.HIGH)
    GPIO.output(ENB, GPIO.HIGH)

def stop_all():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    GPIO.output(ENA, GPIO.LOW)
    GPIO.output(ENB, GPIO.LOW)

# === Step Movement Commands (Fixed time) ===
def move_forward_step(step_time=0.1):
    print("Step: Forward")
    set_motor_direction_forward()
    time.sleep(step_time)
    stop_all()

def move_backward_step(step_time=0.1):
    print("Step: Backward")
    set_motor_direction_backward()
    time.sleep(step_time)
    stop_all()

def turn_right_step(step_time=0.1):
    print("Step: Turn Right")
    set_motor_direction_turn_right()
    time.sleep(step_time)
    stop_all()

def turn_left_step(step_time=0.1):
    print("Step: Turn Left")
    set_motor_direction_turn_left()
    time.sleep(step_time)
    stop_all()

# === Demo Sequence ===
def demo_steps():
    move_forward_step()
    time.sleep(0.5)
    move_backward_step()
    time.sleep(0.5)
    turn_right_step()
    time.sleep(0.5)
    turn_left_step()

# === Main ===
if __name__ == "__main__":
    try:
        print("Jetson GPIO Motor Control - Step-Based")
        demo_steps()

    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    finally:
        stop_all()
        GPIO.cleanup()
        print("GPIO cleanup complete.")
