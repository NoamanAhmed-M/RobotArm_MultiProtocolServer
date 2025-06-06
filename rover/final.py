import Jetson.GPIO as GPIO
import time
import os

# ==== PWM setup via sysfs ====
PWM_CHIP = "0"  # Usually pwmchip0 on Jetson Nano
PWM_LEFT_CH = "0"   # Motor A -> typically on Pin 33 (GPIO13 -> PWM1)
PWM_RIGHT_CH = "1"  # Motor B -> typically on Pin 32 (GPIO12 -> PWM0)

# Export the PWM channel if it's not already exported
def export_pwm(channel):
    path = f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{channel}"
    if not os.path.exists(path):
        try:
            with open(f"/sys/class/pwm/pwmchip{PWM_CHIP}/export", 'w') as f:
                f.write(channel)
            time.sleep(0.1)
        except OSError as e:
            print(f"[!] Export failed for pwm{channel}: {e}")

# Apply PWM signal with a given duty cycle percentage (0-100)
def apply_pwm(duty_percent=70):
    print(f"Applying {duty_percent}% PWM")

    period_ns = 1000000  # 1 ms = 1 kHz frequency
    duty_ns = int(period_ns * duty_percent / 100)

    for channel in [PWM_LEFT_CH, PWM_RIGHT_CH]:
        export_pwm(channel)
        path = f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{channel}"
        try:
            with open(f"{path}/period", 'w') as f:
                f.write(str(period_ns))
            with open(f"{path}/duty_cycle", 'w') as f:
                f.write(str(duty_ns))
            with open(f"{path}/enable", 'w') as f:
                f.write("1")
        except OSError as e:
            print(f"[!] Failed to apply PWM on pwm{channel}: {e}")

# Stop PWM output and unexport channels
def stop_pwm():
    for channel in [PWM_LEFT_CH, PWM_RIGHT_CH]:
        path = f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{channel}"
        try:
            with open(f"{path}/enable", 'w') as f:
                f.write("0")
            with open(f"/sys/class/pwm/pwmchip{PWM_CHIP}/unexport", 'w') as f:
                f.write(channel)
        except:
            pass  # Ignore errors if already unexported

# ==== Motor direction control using Jetson GPIO ====
GPIO.setmode(GPIO.BOARD)  # Use physical pin numbering

# Motor direction pins
IN1 = 7     # Motor A direction 1
IN2 = 11    # Motor A direction 2
IN3 = 13    # Motor B direction 1
IN4 = 15    # Motor B direction 2

# Initialize all direction pins as outputs and set them LOW
for pin in [IN1, IN2, IN3, IN4]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# ==== Movement functions ====

# Move both motors forward at a given duty cycle (speed)
def move_forward(duty=70):
    print("Moving forward")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    apply_pwm(duty)

# Stop all motor movement and disable PWM
def stop_all():
    print("Stopping all motors")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    stop_pwm()

# ==== Test run ====

try:
    move_forward(70)  # Move forward at 70% speed
    time.sleep(2)     # Run for 2 seconds
    stop_all()        # Stop motors
finally:
    GPIO.cleanup()    # Clean up GPIO configuration on exit
