#!/usr/bin/env python3
import Jetson.GPIO as GPIO
import time

# === Pin Definitions ===
# Motor A
IN1 = 7    # Pin 21
IN2 = 11   # Pin 22
ENA = 13   # Pin 32

# Motor B
IN3 = 27   # Pin 23
IN4 = 16   # Pin 24
ENB = 18   # Pin 33

# === GPIO Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)  # Suppress warnings

for pin in [IN1, IN2, ENA, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# Initialize PWM objects
pwm_a = GPIO.PWM(ENA, 1000)  # 1kHz frequency
pwm_b = GPIO.PWM(ENB, 1000)  # 1kHz frequency
pwm_a.start(0)  # Start with 0% duty cycle
pwm_b.start(0)

# === Motor Control Functions ===
def set_motor_direction(motor, direction):
    """Set motor direction: 'forward', 'backward', or 'stop'"""
    if motor == 'A':
        if direction == 'forward':
            GPIO.output(IN1, GPIO.HIGH)
            GPIO.output(IN2, GPIO.LOW)
        elif direction == 'backward':
            GPIO.output(IN1, GPIO.LOW)
            GPIO.output(IN2, GPIO.HIGH)
        else:  # stop
            GPIO.output(IN1, GPIO.LOW)
            GPIO.output(IN2, GPIO.LOW)
    elif motor == 'B':
        if direction == 'forward':
            GPIO.output(IN3, GPIO.HIGH)
            GPIO.output(IN4, GPIO.LOW)
        elif direction == 'backward':
            GPIO.output(IN3, GPIO.LOW)
            GPIO.output(IN4, GPIO.HIGH)
        else:  # stop
            GPIO.output(IN3, GPIO.LOW)
            GPIO.output(IN4, GPIO.LOW)

def set_motor_speed(motor, speed):
    """Set motor speed (0-100)"""
    speed = max(0, min(100, speed))  # Clamp between 0-100
    if motor == 'A':
        pwm_a.ChangeDutyCycle(speed)
    elif motor == 'B':
        pwm_b.ChangeDutyCycle(speed)

def motors_forward(speed_a, speed_b, duration):
    """Move both motors forward with individual speed control"""
    print(f"Moving forward - Motor A: {speed_a*100}%, Motor B: {speed_b*100}%")
    set_motor_direction('A', 'forward')
    set_motor_direction('B', 'forward')
    set_motor_speed('A', speed_a * 100)
    set_motor_speed('B', speed_b * 100)
    time.sleep(duration)

def motors_backward(speed_a, speed_b, duration):
    """Move both motors backward with individual speed control"""
    print(f"Moving backward - Motor A: {speed_a*100}%, Motor B: {speed_b*100}%")
    set_motor_direction('A', 'backward')
    set_motor_direction('B', 'backward')
    set_motor_speed('A', speed_a * 100)
    set_motor_speed('B', speed_b * 100)
    time.sleep(duration)

def turn_left(speed_a, speed_b, duration):
    """Turn left by moving motors in opposite directions"""
    print(f"Turning left - Motor A: backward {speed_a*100}%, Motor B: forward {speed_b*100}%")
    set_motor_direction('A', 'backward')
    set_motor_direction('B', 'forward')
    set_motor_speed('A', speed_a * 100)
    set_motor_speed('B', speed_b * 100)
    time.sleep(duration)

def turn_right(speed_a, speed_b, duration):
    """Turn right by moving motors in opposite directions"""
    print(f"Turning right - Motor A: forward {speed_a*100}%, Motor B: backward {speed_b*100}%")
    set_motor_direction('A', 'forward')
    set_motor_direction('B', 'backward')
    set_motor_speed('A', speed_a * 100)
    set_motor_speed('B', speed_b * 100)
    time.sleep(duration)

def stop_all():
    """Stop both motors"""
    print("Stopping all motors")
    set_motor_direction('A', 'stop')
    set_motor_direction('B', 'stop')
    set_motor_speed('A', 0)
    set_motor_speed('B', 0)

def cleanup():
    """Clean up GPIO resources"""
    stop_all()
    pwm_a.stop()
    pwm_b.stop()
    GPIO.cleanup()
    print("GPIO cleanup complete.")

# === Test Functions ===
def test_individual_motors():
    """Test each motor individually to verify wiring"""
    print("\n=== Testing Individual Motors ===")
    
    # Test Motor A Forward
    print("Testing Motor A - Forward")
    set_motor_direction('A', 'forward')
    set_motor_speed('A', 50)
    time.sleep(2)
    stop_all()
    time.sleep(1)
    
    # Test Motor A Backward
    print("Testing Motor A - Backward")
    set_motor_direction('A', 'backward')
    set_motor_speed('A', 50)
    time.sleep(2)
    stop_all()
    time.sleep(1)
    
    # Test Motor B Forward
    print("Testing Motor B - Forward")
    set_motor_direction('B', 'forward')
    set_motor_speed('B', 50)
    time.sleep(2)
    stop_all()
    time.sleep(1)
    
    # Test Motor B Backward
    print("Testing Motor B - Backward")
    set_motor_direction('B', 'backward')
    set_motor_speed('B', 50)
    time.sleep(2)
    stop_all()
    time.sleep(1)

def test_movement_patterns():
    """Test various movement patterns"""
    print("\n=== Testing Movement Patterns ===")
    
    # Forward movement
    print("Moving forward...")
    motors_forward(0.5, 0.43, 3)
    stop_all()
    time.sleep(1)
    
    # Backward movement
    print("Moving backward...")
    motors_backward(0.5, 0.43, 3)
    stop_all()
    time.sleep(1)
    
    # Left turn
    print("Turning left...")
    turn_left(0.4, 0.4, 2)
    stop_all()
    time.sleep(1)
    
    # Right turn
    print("Turning right...")
    turn_right(0.4, 0.4, 2)
    stop_all()
    time.sleep(1)

# === Main Execution ===
if __name__ == "__main__":
    try:
        print("Jetson Nano Motor Control Test")
        print("==============================")
        
        # Uncomment the test you want to run:
        
        # Test individual motors first
        test_individual_motors()
        
        # Test movement patterns
        test_movement_patterns()
        
        print("\nAll tests completed successfully!")
        
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cleanup()
