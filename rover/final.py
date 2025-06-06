#!/usr/bin/env python3
import Jetson.GPIO as GPIO
import time
import math

# === Pin Definitions ===
# Motor A
IN1 = 7    # Pin 21
IN2 = 11   # Pin 22
ENA = 13   # Pin 32

# Motor B
IN3 = 27   # Pin 23
IN4 = 16   # Pin 24
ENB = 18   # Pin 33

# === Calibration Constants ===
# These need to be calibrated for your specific robot
WHEEL_DIAMETER_MM = 65.0        # Diameter of your wheels in mm
WHEEL_BASE_MM = 150.0           # Distance between wheels in mm
MOTOR_SPEED_FORWARD = 0.7       # Default forward speed (0.0 to 1.0)
MOTOR_SPEED_TURN = 0.6          # Default turning speed (0.0 to 1.0)

# Calibration factors (adjust these based on testing)
MM_PER_SECOND_CALIBRATION = 85.0    # How many mm your robot moves per second at default speed
DEGREES_PER_SECOND_CALIBRATION = 120.0  # How many degrees your robot turns per second at default speed

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
        # Turn on both motors according to their respective duty cycles
        if duty_a > 0:
            GPIO.output(pin_a, GPIO.HIGH)
        if duty_b > 0:
            GPIO.output(pin_b, GPIO.HIGH)
        
        # Run for the minimum on-time
        time.sleep(min(on_time_a, on_time_b))
        
        # Turn off individual motors if needed
        if on_time_a <= on_time_b:
            GPIO.output(pin_a, GPIO.LOW)
            time.sleep(on_time_b - on_time_a)
            GPIO.output(pin_b, GPIO.LOW)
        else:
            GPIO.output(pin_b, GPIO.LOW)
            time.sleep(on_time_a - on_time_b)
            GPIO.output(pin_a, GPIO.LOW)
        
        # Wait for off period
        off_time = period - max(on_time_a, on_time_b)
        if off_time > 0:
            time.sleep(off_time)

# === Low-level Motor Control Functions ===
def set_motor_direction_forward():
    """Set both motors to forward direction"""
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)

def set_motor_direction_backward():
    """Set both motors to backward direction"""
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)

def set_motor_direction_turn_right():
    """Set motors for right turn: Motor A forward, Motor B backward"""
    GPIO.output(IN1, GPIO.HIGH)  # Motor A forward
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)  # Motor B backward
    GPIO.output(IN4, GPIO.LOW)

def set_motor_direction_turn_left():
    """Set motors for left turn: Motor A backward, Motor B forward"""
    GPIO.output(IN1, GPIO.LOW)   # Motor A backward
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)   # Motor B forward
    GPIO.output(IN4, GPIO.HIGH)

def stop_all():
    """Stop all motors"""
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    GPIO.output(ENA, GPIO.LOW)
    GPIO.output(ENB, GPIO.LOW)

# === Distance and Angle Calculation Functions ===
def calculate_time_for_distance(distance_mm, speed=MOTOR_SPEED_FORWARD):
    """Calculate time needed to travel a given distance in mm"""
    speed_mm_per_sec = MM_PER_SECOND_CALIBRATION * speed
    return abs(distance_mm) / speed_mm_per_sec

def calculate_time_for_angle(degrees, speed=MOTOR_SPEED_TURN):
    """Calculate time needed to turn a given angle in degrees"""
    degrees_per_sec = DEGREES_PER_SECOND_CALIBRATION * speed
    return abs(degrees) / degrees_per_sec

# === High-level Movement Functions ===
def move_forward_mm(distance_mm, speed=MOTOR_SPEED_FORWARD):
    """Move forward by specified distance in millimeters"""
    if distance_mm <= 0:
        print(f"Invalid distance: {distance_mm}mm. Must be positive.")
        return
    
    duration = calculate_time_for_distance(distance_mm, speed)
    print(f"Moving forward {distance_mm}mm (estimated {duration:.2f} seconds)...")
    
    set_motor_direction_forward()
    # Adjust individual motor speeds if needed for straight movement
    synchronized_pwm(ENA, ENB, speed * 0.4, speed * 1.0, 100, duration)
    stop_all()

def move_backward_mm(distance_mm, speed=MOTOR_SPEED_FORWARD):
    """Move backward by specified distance in millimeters"""
    if distance_mm <= 0:
        print(f"Invalid distance: {distance_mm}mm. Must be positive.")
        return
    
    duration = calculate_time_for_distance(distance_mm, speed)
    print(f"Moving backward {distance_mm}mm (estimated {duration:.2f} seconds)...")
    
    set_motor_direction_backward()
    # Adjust individual motor speeds if needed for straight movement
    synchronized_pwm(ENA, ENB, speed * 0.4, speed * 1.0, 100, duration)
    stop_all()

def turn_right_degrees(degrees, speed=MOTOR_SPEED_TURN):
    """Turn right by specified degrees"""
    if degrees <= 0:
        print(f"Invalid angle: {degrees}°. Must be positive.")
        return
    
    duration = calculate_time_for_angle(degrees, speed)
    print(f"Turning right {degrees}° (estimated {duration:.2f} seconds)...")
    
    set_motor_direction_turn_right()
    synchronized_pwm(ENA, ENB, speed, speed, 100, duration)
    stop_all()

def turn_left_degrees(degrees, speed=MOTOR_SPEED_TURN):
    """Turn left by specified degrees"""
    if degrees <= 0:
        print(f"Invalid angle: {degrees}°. Must be positive.")
        return
    
    duration = calculate_time_for_angle(degrees, speed)
    print(f"Turning left {degrees}° (estimated {duration:.2f} seconds)...")
    
    set_motor_direction_turn_left()
    synchronized_pwm(ENA, ENB, speed, speed, 100, duration)
    stop_all()

# === Calibration Functions ===
def calibrate_distance():
    """Helper function to calibrate distance movement"""
    print("=== Distance Calibration ===")
    print("1. Measure and mark a 500mm distance")
    print("2. Place robot at start position")
    print("3. Press Enter to move forward 500mm")
    input("Press Enter to continue...")
    
    start_time = time.time()
    move_forward_mm(500)
    actual_time = time.time() - start_time
    
    print(f"Robot moved for {actual_time:.2f} seconds")
    print("Measure the actual distance traveled and update MM_PER_SECOND_CALIBRATION")
    print(f"Current value: {MM_PER_SECOND_CALIBRATION}")
    print(f"If robot traveled X mm, new calibration = {500/actual_time:.1f}")

def calibrate_rotation():
    """Helper function to calibrate rotation"""
    print("=== Rotation Calibration ===")
    print("1. Mark robot's starting orientation")
    print("2. Press Enter to turn 360 degrees")
    input("Press Enter to continue...")
    
    start_time = time.time()
    turn_right_degrees(360)
    actual_time = time.time() - start_time
    
    print(f"Robot turned for {actual_time:.2f} seconds")
    print("Measure the actual angle turned and update DEGREES_PER_SECOND_CALIBRATION")
    print(f"Current value: {DEGREES_PER_SECOND_CALIBRATION}")
    print(f"If robot turned X degrees, new calibration = {360/actual_time:.1f}")

# === Demo Functions ===
def demo_square_pattern():
    """Demo: Move in a square pattern"""
    print("=== Demo: Square Pattern ===")
    side_length = 200  # 200mm sides
    
    for i in range(4):
        move_forward_mm(side_length)
        time.sleep(0.5)
        turn_right_degrees(90)
        time.sleep(0.5)
    
    print("Square pattern complete!")

def demo_movements():
    """Demo various movements"""
    print("=== Movement Demo ===")
    
    # Forward and backward
    move_forward_mm(300)
    time.sleep(1)
    move_backward_mm(300)
    time.sleep(1)
    
    # Turns
    turn_right_degrees(90)
    time.sleep(1)
    turn_left_degrees(180)
    time.sleep(1)
    turn_right_degrees(90)
    time.sleep(1)
    
    print("Demo complete!")

# === Main Execution ===
# === Main Execution ===
if __name__ == "__main__":
    try:
        print("Jetson GPIO Motor Control - Degrees & Millimeters")
        print("=" * 50)
        print(f"Calibration Settings:")
        print(f"  Distance: {MM_PER_SECOND_CALIBRATION} mm/sec")
        print(f"  Rotation: {DEGREES_PER_SECOND_CALIBRATION} deg/sec")
        print("=" * 50)
        
        # Uncomment the demo you want to run:
        # demo_movements()
        # demo_square_pattern()
        
        # Or run individual commands:
        # move_forward_mm(100)
        # turn_right_degrees(45)
        # move_backward_mm(50)
        # turn_left_degrees(90)
        
        # Uncomment to run calibration:
        calibrate_distance()
        calibrate_rotation()
        
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    finally:
        stop_all()
        GPIO.cleanup()
        print("GPIO cleanup complete.")

