import Jetson.GPIO as GPIO
import time
import os

# ==== PWM setup via sysfs ====
PWM_CHIP = "0"
PWM_LEFT_CH = "2"   # Motor A -> Left motor (Pin 33)
PWM_RIGHT_CH = "0"  # Motor B -> Right motor (Pin 32)

def export_pwm(channel):
    path = f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{channel}"
    if not os.path.exists(path):
        try:
            with open(f"/sys/class/pwm/pwmchip{PWM_CHIP}/export", 'w') as f:
                f.write(channel)
            time.sleep(0.1)
        except OSError as e:
            print(f"[!] Export failed for pwm{channel}: {e}")

# Apply PWM individually to each motor
def set_motor_speed(left_duty=70, right_duty=70):
    print(f"Set speeds - Left: {left_duty}%, Right: {right_duty}%")

    period_ns = 1000000
    left_duty_ns = int(period_ns * left_duty / 100)
    right_duty_ns = int(period_ns * right_duty / 100)

    export_pwm(PWM_LEFT_CH)
    export_pwm(PWM_RIGHT_CH)

    try:
        with open(f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{PWM_LEFT_CH}/period", 'w') as f:
            f.write(str(period_ns))
        with open(f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{PWM_LEFT_CH}/duty_cycle", 'w') as f:
            f.write(str(left_duty_ns))
        with open(f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{PWM_LEFT_CH}/enable", 'w') as f:
            f.write("1")

        with open(f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{PWM_RIGHT_CH}/period", 'w') as f:
            f.write(str(period_ns))
        with open(f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{PWM_RIGHT_CH}/duty_cycle", 'w') as f:
            f.write(str(right_duty_ns))
        with open(f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{PWM_RIGHT_CH}/enable", 'w') as f:
            f.write("1")

    except OSError as e:
        print(f"[!] Failed to apply PWM: {e}")

def stop_pwm():
    for channel in [PWM_LEFT_CH, PWM_RIGHT_CH]:
        path = f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{channel}"
        try:
            with open(f"{path}/enable", 'w') as f:
                f.write("0")
            with open(f"/sys/class/pwm/pwmchip{PWM_CHIP}/unexport", 'w') as f:
                f.write(channel)
        except:
            pass

# ==== GPIO Setup ====
GPIO.setmode(GPIO.BOARD)

# Motor direction pins
IN1 = 7     # Left motor (A)
IN2 = 11
IN3 = 13    # Right motor (B)
IN4 = 15

for pin in [IN1, IN2, IN3, IN4]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# ==== Movement Functions ====

def move_forward(left_duty=70, right_duty=70):
    print("Moving forward")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    set_motor_speed(left_duty, right_duty)

def move_backward(left_duty=70, right_duty=70):
    print("Moving backward")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    set_motor_speed(left_duty, right_duty)

def turn_left(duty=70):
    print("Turning left")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    set_motor_speed(duty, 0)  # Only left motor runs

def turn_right(duty=70):
    print("Turning right")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    set_motor_speed(0, duty)  # Only right motor runs

def stop_all():
    print("Stopping all motors")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    stop_pwm()

# ==== Test ====

try:
    move_forward(70, 70)
    time.sleep(2)

    turn_left(60)
    time.sleep(1)

    turn_right(60)
    time.sleep(1)

    move_backward(50, 50)
    time.sleep(2)

    stop_all()
finally:
    GPIO.cleanup()
