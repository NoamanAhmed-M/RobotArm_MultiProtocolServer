#!/usr/bin/env python3
import Jetson.GPIO as GPIO
import time
import math

# === Pin Definitions ===
# Motor A
IN1 = 4    # Grigio -> Pin 7 (GPIO4)
IN2 = 17   # Giallo -> Pin 11 (GPIO17)
ENA = 13   # Viola -> Pin 33 (GPIO13)

# Motor B
IN3 = 27   # Blu -> Pin 13 (GPIO27)
IN4 = 22   # Verde -> Pin 15 (GPIO22)
ENB = 12   # Bianco -> Pin 32 (GPIO12)

# === Calibration Constants ===
WHEEL_DIAMETER_MM = 65.0
WHEEL_BASE_MM = 150.0
MOTOR_SPEED_FORWARD = 0.7
MOTOR_SPEED_TURN = 0.6

MM_PER_SECOND_CALIBRATION = 85.0
DEGREES_PER_SECOND_CALIBRATION = 120.0

PWM_LEFT_RATIO = 0.45
PWM_RIGHT_RATIO = 1.0

# === GPIO Setup ===
GPIO.setmode(GPIO.BCM)
for pin in [IN1, IN2, ENA, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# === Custom Dual PWM Function ===
def synchronized_pwm(pin_a, pin_b, duty_a, duty_b, frequency, duration):
    period = 1.0 / frequency
    on_time_a = period * duty_a
    on_time_b = period * duty_b
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
        
        off_time = period - max(on_time_a, on_time_b)
        if off_time > 0:
            time.sleep(off_time)

# === Low-level Motor Control ===
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
    GPIO.output(ENA, GPIO.LOW)
    GPIO.output(ENB, GPIO.LOW)

# === Motion Time Calculations ===
def calculate_time_for_distance(distance_mm, speed=MOTOR_SPEED_FORWARD):
    speed_mm_per_sec = MM_PER_SECOND_CALIBRATION * speed
    return abs(distance_mm) / speed_mm_per_sec

def calculate_time_for_angle(degrees, speed=MOTOR_SPEED_TURN):
    degrees_per_sec = DEGREES_PER_SECOND_CALIBRATION * speed
    return abs(degrees) / degrees_per_sec

# === High-level Motion ===
def move_forward_mm(distance_mm, speed=MOTOR_SPEED_FORWARD):
    if distance_mm <= 0:
        print(f"Invalid distance: {distance_mm}mm. Must be positive.")
        return
    duration = calculate_time_for_distance(distance_mm, speed)
    print(f"Moving forward {distance_mm}mm (estimated {duration:.2f} seconds)...")
    set_motor_direction_forward()
    synchronized_pwm(ENA, ENB, speed * PWM_LEFT_RATIO, speed * PWM_RIGHT_RATIO, 100, duration)
    stop_all()

def move_backward_mm(distance_mm, speed=MOTOR_SPEED_FORWARD):
    if distance_mm <= 0:
        print(f"Invalid distance: {distance_mm}mm. Must be positive.")
        return
    duration = calculate_time_for_distance(distance_mm, speed)
    print(f"Moving backward {distance_mm}mm (estimated {duration:.2f} seconds)...")
    set_motor_direction_backward()
    synchronized_pwm(ENA, ENB, speed * PWM_LEFT_RATIO, speed * PWM_RIGHT_RATIO, 100, duration)
    stop_all()

def turn_right_degrees(degrees, speed=MOTOR_SPEED_TURN):
    if degrees <= 0:
        print(f"Invalid angle: {degrees}°. Must be positive.")
        return
    duration = calculate_time_for_angle(degrees, speed)
    print(f"Turning right {degrees}° (estimated {duration:.2f} seconds)...")
    set_motor_direction_turn_right()
    synchronized_pwm(ENA, ENB, speed, speed, 100, duration)
    stop_all()

def turn_left_degrees(degrees, speed=MOTOR_SPEED_TURN):
    if degrees <= 0:
        print(f"Invalid angle: {degrees}°. Must be positive.")
        return
    duration = calculate_time_for_angle(degrees, speed)
    print(f"Turning left {degrees}° (estimated {duration:.2f} seconds)...")
    set_motor_direction_turn_left()
    synchronized_pwm(ENA, ENB, speed, speed, 100, duration)
    stop_all()

# === Demo ===
def demo_square_pattern():
    print("=== Demo: Square Pattern ===")
    side_length = 200
    for i in range(4):
        move_forward_mm(side_length)
        time.sleep(0.5)
        turn_right_degrees(90)
        time.sleep(0.5)
    print("Square pattern complete!")

def demo_movements():
    print("=== Movement Demo ===")
    move_forward_mm(300)
    time.sleep(1)
    move_backward_mm(300)
    time.sleep(1)
    turn_right_degrees(90)
    time.sleep(1)
    turn_left_degrees(180)
    time.sleep(1)
    turn_right_degrees(90)
    time.sleep(1)
    print("Demo complete!")

# === Main ===
if __name__ == "__main__":
    try:
        print("Jetson GPIO Motor Control - Degrees & Millimeters")
        print("=" * 50)
        print(f"Calibration Settings:")
        print(f"  Distance: {MM_PER_SECOND_CALIBRATION} mm/sec")
        print(f"  Rotation: {DEGREES_PER_SECOND_CALIBRATION} deg/sec")
        print(f"  PWM Balance: Left={PWM_LEFT_RATIO}, Right={PWM_RIGHT_RATIO}")
        print("=" * 50)

        demo_movements()
        # demo_square_pattern()

    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    finally:
        stop_all()
        GPIO.cleanup()
        print("GPIO cleanup complete.")
