#!/usr/bin/env python3
import Jetson.GPIO as GPIO
import time
import json
import os

# === Pin Definitions ===
IN1 = 7
IN2 = 11
ENA = 13
IN3 = 27
IN4 = 16
ENB = 18

# === Robot Constants ===
WHEEL_DIAMETER_MM = 65.0
WHEEL_BASE_MM = 150.0
MOTOR_SPEED_FORWARD = 0.7
MOTOR_SPEED_TURN = 0.6

# === PWM Balance Tuning ===
PWM_LEFT_RATIO = 0.31
PWM_RIGHT_RATIO = 1.0

# === Calibration File ===
CALIBRATION_FILE = "calibration.json"

# === Load/Save Calibration ===
def load_calibration():
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE, "r") as f:
            return json.load(f)
    else:
        return {
            "MM_PER_SECOND_CALIBRATION": 85.0,
            "DEGREES_PER_SECOND_CALIBRATION": 120.0
        }

def save_calibration(data):
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(data, f, indent=2)
        print(f"\nSaved calibration to {CALIBRATION_FILE}")

calibration = load_calibration()
MM_PER_SECOND_CALIBRATION = calibration["MM_PER_SECOND_CALIBRATION"]
DEGREES_PER_SECOND_CALIBRATION = calibration["DEGREES_PER_SECOND_CALIBRATION"]

# === GPIO Setup ===
GPIO.setmode(GPIO.BCM)
for pin in [IN1, IN2, ENA, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# === PWM Function ===
def synchronized_pwm(pin_a, pin_b, duty_a, duty_b, frequency, duration):
    period = 1.0 / frequency
    on_time_a = period * duty_a
    on_time_b = period * duty_b
    end_time = time.time() + duration
    while time.time() < end_time:
        if duty_a > 0: GPIO.output(pin_a, GPIO.HIGH)
        if duty_b > 0: GPIO.output(pin_b, GPIO.HIGH)
        time.sleep(min(on_time_a, on_time_b))
        if on_time_a <= on_time_b:
            GPIO.output(pin_a, GPIO.LOW)
            time.sleep(on_time_b - on_time_a)
            GPIO.output(pin_b, GPIO.LOW)
        else:
            GPIO.output(pin_b, GPIO.LOW)
            time.sleep(on_time_a - on_time_b)
            GPIO.output(pin_a, GPIO.LOW)
        time.sleep(period - max(on_time_a, on_time_b))

# === Motor Directions ===
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

# === Time Calculations ===
def calculate_time_for_distance(distance_mm, speed=MOTOR_SPEED_FORWARD):
    return abs(distance_mm) / (MM_PER_SECOND_CALIBRATION * speed)

def calculate_time_for_angle(degrees, speed=MOTOR_SPEED_TURN):
    return abs(degrees) / (DEGREES_PER_SECOND_CALIBRATION * speed)

# === Movement ===
def move_forward_mm(distance_mm, speed=MOTOR_SPEED_FORWARD):
    duration = calculate_time_for_distance(distance_mm, speed)
    print(f"Moving forward {distance_mm}mm (est. {duration:.2f}s)")
    set_motor_direction_forward()
    synchronized_pwm(ENA, ENB, speed * PWM_LEFT_RATIO, speed * PWM_RIGHT_RATIO, 100, duration)
    stop_all()

def move_backward_mm(distance_mm, speed=MOTOR_SPEED_FORWARD):
    duration = calculate_time_for_distance(distance_mm, speed)
    print(f"Moving backward {distance_mm}mm (est. {duration:.2f}s)")
    set_motor_direction_backward()
    synchronized_pwm(ENA, ENB, speed * PWM_LEFT_RATIO, speed * PWM_RIGHT_RATIO, 100, duration)
    stop_all()

def turn_right_degrees(degrees, speed=MOTOR_SPEED_TURN):
    duration = calculate_time_for_angle(degrees, speed)
    print(f"Turning right {degrees}° (est. {duration:.2f}s)")
    set_motor_direction_turn_right()
    synchronized_pwm(ENA, ENB, speed, speed, 100, duration)
    stop_all()

def turn_left_degrees(degrees, speed=MOTOR_SPEED_TURN):
    duration = calculate_time_for_angle(degrees, speed)
    print(f"Turning left {degrees}° (est. {duration:.2f}s)")
    set_motor_direction_turn_left()
    synchronized_pwm(ENA, ENB, speed, speed, 100, duration)
    stop_all()

# === Calibration ===
def calibrate_distance():
    print("=== Calibrate Distance ===")
    print("1. Mark exactly 500mm")
    input("2. Press Enter to move forward 500mm...")
    start_time = time.time()
    move_forward_mm(500)
    elapsed = time.time() - start_time
    print(f"Time taken: {elapsed:.2f} sec")
    actual_mm = float(input("Enter actual distance moved in mm: "))
    new_calibration = actual_mm / elapsed
    print(f"New MM_PER_SECOND_CALIBRATION = {new_calibration:.1f}")
    calibration["MM_PER_SECOND_CALIBRATION"] = new_calibration
    save_calibration(calibration)

def calibrate_rotation():
    print("=== Calibrate Rotation ===")
    input("Press Enter to rotate 360°...")
    start_time = time.time()
    turn_right_degrees(360)
    elapsed = time.time() - start_time
    print(f"Time taken: {elapsed:.2f} sec")
    actual_degrees = float(input("Enter actual angle turned in degrees: "))
    new_calibration = actual_degrees / elapsed
    print(f"New DEGREES_PER_SECOND_CALIBRATION = {new_calibration:.1f}")
    calibration["DEGREES_PER_SECOND_CALIBRATION"] = new_calibration
    save_calibration(calibration)

# === Main ===
if __name__ == "__main__":
    try:
        print("=== Jetson Nano Robot Calibration ===")
        print(f"Distance speed: {MM_PER_SECOND_CALIBRATION} mm/s")
        print(f"Rotation speed: {DEGREES_PER_SECOND_CALIBRATION} deg/s")
        print(f"PWM balance: Left={PWM_LEFT_RATIO}, Right={PWM_RIGHT_RATIO}")
        calibrate_distance()
        calibrate_rotation()
    except KeyboardInterrupt:
        print("\n[Interrupted by user]")
    finally:
        stop_all()
        GPIO.cleanup()
        print("GPIO cleanup done.")
{
  "MM_PER_SECOND_CALIBRATION": 21.205838275937857,
  "DEGREES_PER_SECOND_CALIBRATION": 143.8565585853301
}
