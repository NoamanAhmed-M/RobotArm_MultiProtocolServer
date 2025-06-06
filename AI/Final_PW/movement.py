# movement.py
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

# === Calibration Constants ===
MM_PER_SECOND_CALIBRATION = 21.205838275937857
DEGREES_PER_SECOND_CALIBRATION = 143.8565585853301

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

        time.sleep(period - max(on_time_a, on_time_b))

# === Motor Control Functions ===
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

# === Movement Functions ===
def move_forward_mm(distance_mm, speed=0.7):
    duration = abs(distance_mm) / (MM_PER_SECOND_CALIBRATION * speed)
    print(f"Moving forward {distance_mm}mm (est. {duration:.2f}s)")
    set_motor_direction_forward()
    synchronized_pwm(ENA, ENB, speed * PWM_LEFT_RATIO, speed * PWM_RIGHT_RATIO, 100, duration)
    stop_all()

def turn_left_quick():
    print("Turning left (quick step)")
    set_motor_direction_turn_left()
    synchronized_pwm(ENA, ENB, 0.6, 0.6, 100, 0.25)  # quick turn
    stop_all()

def turn_right_quick():
    print("Turning right (quick step)")
    set_motor_direction_turn_right()
    synchronized_pwm(ENA, ENB, 0.6, 0.6, 100, 0.25)  # quick turn
    stop_all()

def cleanup():
    stop_all()
    GPIO.cleanup()

# === Grid Step Navigation ===
def execute_path(path, step_distance_mm=100):
    print(f"Executing path with {len(path)} steps")
    if len(path) < 2:
        return

    # Assume starting direction is "up" (0, -1)
    current_direction = (0, -1)

    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        dx = x2 - x1
        dy = y2 - y1
        next_direction = (dx, dy)

        if next_direction != current_direction:
            # Determine rotation direction
            if current_direction == (0, -1):  # Up
                if next_direction == (1, 0):
                    turn_right_quick()
                elif next_direction == (-1, 0):
                    turn_left_quick()
                elif next_direction == (0, 1):
                    turn_right_quick()
                    turn_right_quick()
            elif current_direction == (0, 1):  # Down
                if next_direction == (1, 0):
                    turn_left_quick()
                elif next_direction == (-1, 0):
                    turn_right_quick()
                elif next_direction == (0, -1):
                    turn_right_quick()
                    turn_right_quick()
            elif current_direction == (1, 0):  # Right
                if next_direction == (0, -1):
                    turn_left_quick()
                elif next_direction == (0, 1):
                    turn_right_quick()
                elif next_direction == (-1, 0):
                    turn_right_quick()
                    turn_right_quick()
            elif current_direction == (-1, 0):  # Left
                if next_direction == (0, -1):
                    turn_right_quick()
                elif next_direction == (0, 1):
                    turn_left_quick()
                elif next_direction == (1, 0):
                    turn_right_quick()
                    turn_right_quick()

            current_direction = next_direction

        move_forward_mm(step_distance_mm)
