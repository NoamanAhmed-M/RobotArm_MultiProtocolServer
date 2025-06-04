#!/usr/bin/env python3

import Jetson.GPIO as GPIO
import time
import cv2
import numpy as np
import threading
from collections import deque
import math

# === Pin Definitions ===
# Motor A
IN1 = 9    # Pin 21
IN2 = 10   # Pin 22
ENA = 18   # Pin 32

# Motor B
IN3 = 11   # Pin 23
IN4 = 8    # Pin 24
ENB = 19   # Pin 33

# === Setup ===
GPIO.setmode(GPIO.BCM)

for pin in [IN1, IN2, ENA, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# === Global Variables ===
target_object = None
obstacle_map = {}
current_position = {'x': 0, 'y': 0, 'angle': 0}
navigation_path = []
detection_active = False
camera = None

# === Software PWM Function ===
def software_pwm(pin, duty_cycle, frequency, duration):
    period = 1.0 / frequency
    on_time = period * duty_cycle
    off_time = period * (1 - duty_cycle)
    end_time = time.time() + duration

    while time.time() < end_time:
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(on_time)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(off_time)

# === Motor Functions ===
def motor_a_forward(speed, duration):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    software_pwm(ENA, speed, 100, duration)

def motor_a_backward(speed, duration):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    software_pwm(ENA, speed, 100, duration)

def motor_b_forward(speed, duration):
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    software_pwm(ENB, speed, 100, duration)

def motor_b_backward(speed, duration):
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    software_pwm(ENB, speed, 100, duration)

def stop_all():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    GPIO.output(ENA, GPIO.LOW)
    GPIO.output(ENB, GPIO.LOW)

# === Advanced Movement Functions ===
def move_forward(speed=0.5, duration=1.0):
    """Move both motors forward"""
    print(f"Moving forward at {speed*100}% speed for {duration}s")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    
    # Run both motors simultaneously
    end_time = time.time() + duration
    period = 1.0 / 100  # 100 Hz frequency
    on_time = period * speed
    off_time = period * (1 - speed)
    
    while time.time() < end_time:
        GPIO.output(ENA, GPIO.HIGH)
        GPIO.output(ENB, GPIO.HIGH)
        time.sleep(on_time)
        GPIO.output(ENA, GPIO.LOW)
        GPIO.output(ENB, GPIO.LOW)
        time.sleep(off_time)
    
    # Update position estimate
    current_position['y'] += duration * speed * 10  # Rough estimate

def move_backward(speed=0.5, duration=1.0):
    """Move both motors backward"""
    print(f"Moving backward at {speed*100}% speed for {duration}s")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    
    end_time = time.time() + duration
    period = 1.0 / 100
    on_time = period * speed
    off_time = period * (1 - speed)
    
    while time.time() < end_time:
        GPIO.output(ENA, GPIO.HIGH)
        GPIO.output(ENB, GPIO.HIGH)
        time.sleep(on_time)
        GPIO.output(ENA, GPIO.LOW)
        GPIO.output(ENB, GPIO.LOW)
        time.sleep(off_time)
    
    current_position['y'] -= duration * speed * 10

def turn_left(speed=0.4, duration=0.5):
    """Turn left by rotating motors in opposite directions"""
    print(f"Turning left at {speed*100}% speed for {duration}s")
    GPIO.output(IN1, GPIO.LOW)   # Motor A backward
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)  # Motor B forward
    GPIO.output(IN4, GPIO.LOW)
    
    end_time = time.time() + duration
    period = 1.0 / 100
    on_time = period * speed
    off_time = period * (1 - speed)
    
    while time.time() < end_time:
        GPIO.output(ENA, GPIO.HIGH)
        GPIO.output(ENB, GPIO.HIGH)
        time.sleep(on_time)
        GPIO.output(ENA, GPIO.LOW)
        GPIO.output(ENB, GPIO.LOW)
        time.sleep(off_time)
    
    current_position['angle'] -= 45  # Rough estimate

def turn_right(speed=0.4, duration=0.5):
    """Turn right by rotating motors in opposite directions"""
    print(f"Turning right at {speed*100}% speed for {duration}s")
    GPIO.output(IN1, GPIO.HIGH)  # Motor A forward
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)   # Motor B backward
    GPIO.output(IN4, GPIO.HIGH)
    
    end_time = time.time() + duration
    period = 1.0 / 100
    on_time = period * speed
    off_time = period * (1 - speed)
    
    while time.time() < end_time:
        GPIO.output(ENA, GPIO.HIGH)
        GPIO.output(ENB, GPIO.HIGH)
        time.sleep(on_time)
        GPIO.output(ENA, GPIO.LOW)
        GPIO.output(ENB, GPIO.LOW)
        time.sleep(off_time)
    
    current_position['angle'] += 45  # Rough estimate

# === Object Detection Functions ===
def initialize_camera():
    """Initialize camera for object detection"""
    global camera
    try:
        camera = cv2.VideoCapture(0)  # Use default camera
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("Camera initialized successfully")
        return True
    except Exception as e:
        print(f"Failed to initialize camera: {e}")
        return False

def detect_objects(duration=2.0):
    """Detect objects for specified duration and create initial map"""
    global target_object, detection_active
    
    if camera is None:
        print("Camera not initialized")
        return None
    
    print(f"Starting object detection for {duration} seconds...")
    detection_active = True
    
    # Simple color-based object detection (you can replace with YOLO/other models)
    detected_objects = []
    end_time = time.time() + duration
    
    while time.time() < end_time and detection_active:
        ret, frame = camera.read()
        if not ret:
            continue
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Example: Detect red objects (adjust HSV ranges as needed)
        lower_red = np.array([0, 50, 50])
        upper_red = np.array([10, 255, 255])
        mask1 = cv2.inRange(hsv, lower_red, upper_red)
        
        lower_red = np.array([170, 50, 50])
        upper_red = np.array([180, 255, 255])
        mask2 = cv2.inRange(hsv, lower_red, upper_red)
        
        mask = mask1 + mask2
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:  # Filter small objects
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                center_x = x + w // 2
                center_y = y + h // 2
                
                # Estimate distance based on object size (rough approximation)
                distance = max(1, 10000 / area)  # Inverse relationship
                
                detected_objects.append({
                    'center': (center_x, center_y),
                    'size': area,
                    'distance': distance,
                    'bbox': (x, y, w, h)
                })
        
        # Small delay to prevent overwhelming the processor
        time.sleep(0.1)
    
    detection_active = False
    
    if detected_objects:
        # Select the largest object as target
        target_object = max(detected_objects, key=lambda obj: obj['size'])
        print(f"Target object detected at distance: {target_object['distance']:.2f}")
        return target_object
    else:
        print("No objects detected")
        return None

def detect_obstacles():
    """Continuously detect obstacles and update map"""
    global obstacle_map
    
    if camera is None:
        return []
    
    ret, frame = camera.read()
    if not ret:
        return []
    
    # Simple obstacle detection using edge detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    # Find contours that might be obstacles
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    obstacles = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 200:  # Filter small noise
            x, y, w, h = cv2.boundingRect(contour)
            center_x = x + w // 2
            
            # Determine if obstacle is on left, center, or right
            frame_width = frame.shape[1]
            if center_x < frame_width // 3:
                position = 'left'
            elif center_x > 2 * frame_width // 3:
                position = 'right'
            else:
                position = 'center'
            
            obstacles.append({
                'position': position,
                'size': area,
                'bbox': (x, y, w, h)
            })
    
    # Update obstacle map
    obstacle_map = {obs['position']: obs for obs in obstacles}
    return obstacles

# === Path Planning Functions ===
def create_initial_path_to_target():
    """Create initial path to target object"""
    global navigation_path, target_object
    
    if target_object is None:
        return []
    
    # Simple path: move forward towards target
    distance = target_object['distance']
    steps = max(1, int(distance / 2))  # Divide journey into steps
    
    navigation_path = []
    for i in range(steps):
        navigation_path.append({
            'action': 'forward',
            'speed': 0.5,
            'duration': 1.0
        })
    
    print(f"Created path with {len(navigation_path)} steps to target")
    return navigation_path

def update_path_for_obstacles(obstacles):
    """Update navigation path to avoid obstacles"""
    global navigation_path
    
    if not obstacles or not navigation_path:
        return navigation_path
    
    # Simple obstacle avoidance strategy
    modified_path = []
    
    for step in navigation_path:
        if step['action'] == 'forward':
            # Check if path is blocked
            center_blocked = any(obs['position'] == 'center' for obs in obstacles)
            left_blocked = any(obs['position'] == 'left' for obs in obstacles)
            right_blocked = any(obs['position'] == 'right' for obs in obstacles)
            
            if center_blocked:
                if not right_blocked:
                    # Turn right, move forward, turn left
                    modified_path.extend([
                        {'action': 'turn_right', 'speed': 0.4, 'duration': 0.5},
                        {'action': 'forward', 'speed': 0.5, 'duration': 1.5},
                        {'action': 'turn_left', 'speed': 0.4, 'duration': 0.5}
                    ])
                elif not left_blocked:
                    # Turn left, move forward, turn right
                    modified_path.extend([
                        {'action': 'turn_left', 'speed': 0.4, 'duration': 0.5},
                        {'action': 'forward', 'speed': 0.5, 'duration': 1.5},
                        {'action': 'turn_right', 'speed': 0.4, 'duration': 0.5}
                    ])
                else:
                    # Both sides blocked, back up and reassess
                    modified_path.append({
                        'action': 'backward', 'speed': 0.5, 'duration': 1.0
                    })
            else:
                # Path clear, proceed as planned
                modified_path.append(step)
        else:
            modified_path.append(step)
    
    navigation_path = modified_path
    print(f"Updated path with {len(navigation_path)} steps (obstacle avoidance)")
    return navigation_path

# === Navigation Execution ===
def execute_navigation_step(step):
    """Execute a single navigation step"""
    action = step['action']
    speed = step.get('speed', 0.5)
    duration = step.get('duration', 1.0)
    
    if action == 'forward':
        move_forward(speed, duration)
    elif action == 'backward':
        move_backward(speed, duration)
    elif action == 'turn_left':
        turn_left(speed, duration)
    elif action == 'turn_right':
        turn_right(speed, duration)
    else:
        print(f"Unknown action: {action}")
    
    # Stop motors after each step
    stop_all()
    time.sleep(0.2)  # Brief pause between actions

def navigate_to_target():
    """Main navigation function"""
    global navigation_path
    
    if not navigation_path:
        print("No navigation path available")
        return
    
    print(f"Starting navigation with {len(navigation_path)} steps")
    
    for i, step in enumerate(navigation_path):
        print(f"Executing step {i+1}/{len(navigation_path)}: {step['action']}")
        
        # Check for obstacles before each step
        obstacles = detect_obstacles()
        if obstacles:
            print(f"Obstacles detected: {[obs['position'] for obs in obstacles]}")
            # Update remaining path
            remaining_path = navigation_path[i:]
            updated_path = update_path_for_obstacles(obstacles)
            navigation_path = navigation_path[:i] + updated_path
        
        # Execute the step
        execute_navigation_step(step)
        
        # Small delay for stability
        time.sleep(0.5)
    
    print("Navigation completed!")

# === Main Autonomous Function ===
def autonomous_navigation():
    """Main function that orchestrates the autonomous navigation"""
    try:
        # Initialize camera
        if not initialize_camera():
            print("Cannot proceed without camera")
            return
        
        print("=== Starting Autonomous Navigation System ===")
        
        # Step 1: Detect target object for 2 seconds
        print("\n1. Object Detection Phase")
        target = detect_objects(duration=2.0)
        
        if target is None:
            print("No target detected. Stopping.")
            return
        
        # Step 2: Create initial path to target
        print("\n2. Path Planning Phase")
        create_initial_path_to_target()
        
        # Step 3: Navigate with obstacle avoidance
        print("\n3. Navigation Phase")
        navigate_to_target()
        
        print("\n=== Mission Complete ===")
        
    except KeyboardInterrupt:
        print("\nNavigation interrupted by user")
    except Exception as e:
        print(f"Error during navigation: {e}")
    finally:
        stop_all()
        if camera:
            camera.release()
        cv2.destroyAllWindows()

# === Main Logic ===
if __name__ == "__main__":
    try:
        # Run the autonomous navigation system
        autonomous_navigation()
        
    finally:
        stop_all()
        GPIO.cleanup()
        if camera:
            camera.release()
        cv2.destroyAllWindows()
        print("GPIO cleanup complete.")
