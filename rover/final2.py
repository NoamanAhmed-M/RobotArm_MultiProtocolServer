#!/usr/bin/env python3
import Jetson.GPIO as GPIO
import time

# IMPORTANT: Only pins 32 and 33 support hardware PWM on Jetson Nano
# Pin 32 = BCM 12 (ENA for Motor A)
# Pin 33 = BCM 13 (ENB for Motor B)

# === Pin Definitions ===
# Motor A
IN1 = 7    # Pin 21
IN2 = 11   # Pin 22
ENA = 12   # Pin 32 (Hardware PWM supported) - BCM 12

# Motor B
IN3 = 27   # Pin 23
IN4 = 16   # Pin 24
ENB = 13   # Pin 33 (Hardware PWM supported) - BCM 13

# === Alternative: Software PWM Implementation ===
# If you can't change wiring, use this section instead:
USE_SOFTWARE_PWM = False  # Set to True if you can't rewire

if USE_SOFTWARE_PWM:
    # Keep your original pin assignments
    ENA = 13   # Pin 32
    ENB = 18   # Pin 33 (will use software PWM)

# === GPIO Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)  # Suppress warnings

for pin in [IN1, IN2, ENA, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# Initialize PWM based on mode
if USE_SOFTWARE_PWM:
    # Software PWM implementation (fallback)
    pwm_a = None
    pwm_b = None
    print("Using software PWM implementation")
else:
    # Hardware PWM (recommended)
    try:
        pwm_a = GPIO.PWM(ENA, 1000)  # 1kHz frequency
        pwm_b = GPIO.PWM(ENB, 1000)  # 1kHz frequency
        pwm_a.start(0)  # Start with 0% duty cycle
        pwm_b.start(0)
        print("Using hardware PWM on pins 32 and 33")
    except ValueError as e:
        print(f"Hardware PWM failed: {e}")
        print("Falling back to software PWM")
        USE_SOFTWARE_PWM = True
        pwm_a = None
        pwm_b = None

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
            GPIO.output(IN3, GPIO.HIGH)
            GPIO.output(IN4, GPIO.LOW)
        else:  # stop
            GPIO.output(IN3, GPIO.LOW)
            GPIO.output(IN4, GPIO.LOW)

def set_motor_speed(motor, speed):
    """Set motor speed (0-100)"""
    speed = max(0, min(100, speed))  # Clamp between 0-100
    
    if USE_SOFTWARE_PWM:
        # Software PWM implementation
        if motor == 'A':
            if speed == 0:
                GPIO.output(ENA, GPIO.LOW)
            else:
                # Simple software PWM - not as smooth as hardware PWM
                GPIO.output(ENA, GPIO.HIGH)
        elif motor == 'B':
            if speed == 0:
                GPIO.output(ENB, GPIO.LOW)
            else:
                GPIO.output(ENB, GPIO.HIGH)
    else:
        # Hardware PWM implementation
        if motor == 'A' and pwm_a:
            pwm_a.ChangeDutyCycle(speed)
        elif motor == 'B' and pwm_b:
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
    if not USE_SOFTWARE_PWM and pwm_a and pwm_b:
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
----------------
Traceback (most recent call last):
  File "led.py", line 26, in <module>
    pwm_b = GPIO.PWM(ENB, 1000)  # 1kHz frequency
  File "/usr/lib/python3/dist-packages/Jetson/GPIO/gpio.py", line 608, in __init__
    self._ch_info = _channel_to_info(channel, need_pwm=True)
  File "/usr/lib/python3/dist-packages/Jetson/GPIO/gpio.py", line 115, in _channel_to_info
    return _channel_to_info_lookup(channel, need_gpio, need_pwm)
  File "/usr/lib/python3/dist-packages/Jetson/GPIO/gpio.py", line 109, in _channel_to_info_lookup
    raise ValueError("Channel %s is not a PWM" % str(channel))
ValueError: Channel 18 is not a PWM
Exception ignored in: <bound method PWM.__del__ of <Jetson.GPIO.gpio.PWM object at 0x7f9df810f0>>
Traceback (most recent call last):
  File "/usr/lib/python3/dist-packages/Jetson/GPIO/gpio.py", line 640, in __del__
    if _channel_configuration.get(self._ch_info.channel, None) != HARD_PWM:
AttributeError: 'PWM' object has no attribute '_ch_info'
