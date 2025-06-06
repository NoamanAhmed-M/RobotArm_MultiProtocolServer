import Jetson.GPIO as GPIO
import time
import os

# ==== PWM via sysfs configuration ====
PWM_CHIP = "0"  # pwmchip0
PWM_LEFT_CH = "0"   # Motor A (pin 33 - GPIO13)
PWM_RIGHT_CH = "1"  # Motor B (pin 32 - GPIO12)

def export_pwm(channel):
    path = f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{channel}"
    if not os.path.exists(path):
        with open(f"/sys/class/pwm/pwmchip{PWM_CHIP}/export", 'w') as f:
            f.write(channel)
        time.sleep(0.1)

def set_pwm(channel, period_ns, duty_ns):
    path = f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{channel}"
    with open(f"{path}/period", 'w') as f:
        f.write(str(period_ns))
    with open(f"{path}/duty_cycle", 'w') as f:
        f.write(str(duty_ns))
    with open(f"{path}/enable", 'w') as f:
        f.write("1")

def stop_pwm(channel):
    path = f"/sys/class/pwm/pwmchip{PWM_CHIP}/pwm{channel}"
    try:
        with open(f"{path}/enable", 'w') as f:
            f.write("0")
        with open(f"/sys/class/pwm/pwmchip{PWM_CHIP}/unexport", 'w') as f:
            f.write(channel)
    except FileNotFoundError:
        pass

# ==== GPIO Motor Direction Configuration ====
GPIO.setmode(GPIO.BOARD)

IN1 = 7     # Motor A dir1
IN2 = 11    # Motor A dir2
IN3 = 13    # Motor B dir1
IN4 = 15    # Motor B dir2

pins = [IN1, IN2, IN3, IN4]
for pin in pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

def apply_pwm(duty_percent):
    period_ns = 1000000  # 1ms = 1kHz
    duty_ns = int(period_ns * (duty_percent / 100.0))

    export_pwm(PWM_LEFT_CH)
    export_pwm(PWM_RIGHT_CH)

    set_pwm(PWM_LEFT_CH, period_ns, duty_ns)
    set_pwm(PWM_RIGHT_CH, period_ns, duty_ns)

def move_forward(duty_percent=70):
    print(f"Moving forward at {duty_percent}% speed")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    apply_pwm(duty_percent)

def move_backward(duty_percent=70):
    print(f"Moving backward at {duty_percent}% speed")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    apply_pwm(duty_percent)

def turn_left(duty_percent=70):
    print(f"Turning left at {duty_percent}% speed")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    apply_pwm(duty_percent)

def turn_right(duty_percent=70):
    print(f"Turning right at {duty_percent}% speed")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    apply_pwm(duty_percent)

def stop_all():
    print("Stopping motors")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    stop_pwm(PWM_LEFT_CH)
    stop_pwm(PWM_RIGHT_CH)

# ==== تجربة التشغيل ====
try:
    move_forward(70)
    time.sleep(2)
    
    turn_left(60)
    time.sleep(1)

    turn_right(60)
    time.sleep(1)

    move_backward(50)
    time.sleep(2)

    stop_all()
finally:
    GPIO.cleanup()
