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

# === Software PWM Function ===
def software_pwm(pin, duty_cycle, frequency, duration):
    period = 1.0 / frequency
    on_time = period * (duty_cycle / 100.0)
    off_time = period - on_time
    end_time = time.time() + duration

    while time.time() < end_time:
        if duty_cycle > 0:
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(on_time)
        if duty_cycle < 100:
            GPIO.output(pin, GPIO.LOW)
            time.sleep(off_time)

# === Dual Software PWM Control ===
def dual_software_pwm(pin_a, duty_a, pin_b, duty_b, frequency, duration):
    period = 1.0 / frequency
    on_time_a = period * (duty_a / 100.0)
    on_time_b = period * (duty_b / 100.0)
    off_time = period - max(on_time_a, on_time_b)
    end_time = time.time() + duration

    while time.time() < end_time:
        if duty_a > 0:
            GPIO.output(pin_a, GPIO.HIGH)
        if duty_b > 0:
            GPIO.output(pin_b, GPIO.HIGH)

        time.sleep(min(on_time_a, on_time_b))

        if on_time_a <= on_time_b:
            GPIO.output(pin_a, GPIO.LOW)
            time.sleep(on_time_b - on_time_a)
            GPIO.output(pin_b, GPIO.LOW)
        else:
            GPIO.output(pin_b, GPIO.LOW)
            time.sleep(on_time_a - on_time_b)
            GPIO.output(pin_a, GPIO.LOW)

        if off_time > 0:
            time.sleep(off_time)

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

# === Movement Step Function Using Dual Software PWM ===
def step_move(direction_fn, speed_left, speed_right, duration=0.1, frequency=100):
    direction_fn()
    dual_software_pwm(ENA, speed_left, ENB, speed_right, frequency, duration)
    stop_all()

# === High-Level Movements ===
def move_forward_step(speed_left=70, speed_right=70, duration=0.1):
    print(f"Forward Step: L={speed_left}%, R={speed_right}%")
    step_move(set_motor_direction_forward, speed_left, speed_right, duration)

def move_backward_step(speed_left=70, speed_right=70, duration=0.1):
    print(f"Backward Step: L={speed_left}%, R={speed_right}%")
    step_move(set_motor_direction_backward, speed_left, speed_right, duration)

def turn_right_step(speed_left=70, speed_right=70, duration=0.1):
    print(f"Turn Right Step: L={speed_left}%, R={speed_right}%")
    step_move(set_motor_direction_turn_right, speed_left, speed_right, duration)

def turn_left_step(speed_left=70, speed_right=70, duration=0.1):
    print(f"Turn Left Step: L={speed_left}%, R={speed_right}%")
    step_move(set_motor_direction_turn_left, speed_left, speed_right, duration)

# === Demo ===
def demo_steps():
    move_forward_step(20, 50, 0.3)
    time.sleep(0.1)
    move_backward_step(20, 50, 0.3)
    time.sleep(0.2)
    turn_right_step(25, 50, 0.3)
    time.sleep(0.2)
    turn_left_step(25, 50, 0.3)

# === Main ===
if __name__ == "__main__":
    try:
        print("Jetson Nano - Step Control with Software PWM")
        demo_steps()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        stop_all()
        GPIO.cleanup()
        print("GPIO cleanup complete.")
