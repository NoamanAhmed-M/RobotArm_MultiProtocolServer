import Jetson.GPIO as GPIO
import time
import os

# Pin Setup
IN1 = 22           # LED2: Direction forward
IN2 = 27           # LED3: Direction backward
PWM_PIN = 32       # This is PHYSICAL pin number, but we control it using PWM interface
PWM_PATH = "/sys/class/pwm/pwmchip0/pwm0"

def export_pwm():
    if not os.path.exists(PWM_PATH):
        with open("/sys/class/pwm/pwmchip0/export", "w") as f:
            f.write("0")
        time.sleep(0.1)

def unexport_pwm():
    if os.path.exists(PWM_PATH):
        with open("/sys/class/pwm/pwmchip0/unexport", "w") as f:
            f.write("0")

def set_pwm(period_ns, duty_ns):
    with open(PWM_PATH + "/period", "w") as f:
        f.write(str(period_ns))
    with open(PWM_PATH + "/duty_cycle", "w") as f:
        f.write(str(duty_ns))
    with open(PWM_PATH + "/enable", "w") as f:
        f.write("1")

def stop_pwm():
    with open(PWM_PATH + "/enable", "w") as f:
        f.write("0")

# Direction LEDs
def direction_forward():
    GPIO.output(IN1, GPIO.HIGH)   # LED2 ON
    GPIO.output(IN2, GPIO.LOW)    # LED3 OFF

def direction_backward():
    GPIO.output(IN1, GPIO.LOW)    # LED2 OFF
    GPIO.output(IN2, GPIO.HIGH)   # LED3 ON

def direction_stop():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    stop_pwm()

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)

export_pwm()

try:
    while True:
        print("Forward at 75% speed")
        direction_forward()
        set_pwm(1000000, 750000)  # 75% brightness on LED1 (PWM)
        time.sleep(3)

        print("Stop")
        direction_stop()
        time.sleep(2)

        print("Backward at 50% speed")
        direction_backward()
        set_pwm(1000000, 500000)  # 50% brightness on LED1 (PWM)
        time.sleep(3)

        print("Stop")
        direction_stop()
        time.sleep(2)

except KeyboardInterrupt:
    print("Program stopped by user")

finally:
    print("Cleaning up...")
    direction_stop()
    unexport_pwm()
    GPIO.cleanup()
