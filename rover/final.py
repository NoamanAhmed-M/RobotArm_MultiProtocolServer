import Jetson.GPIO as GPIO
import time

# Use BOARD numbering mode to match the physical pins on the Jetson Nano
GPIO.setmode(GPIO.BOARD)

# Pin assignments based on your wire colors and connections
IN1 = 7     # Gray wire - Motor A direction 1
IN2 = 11    # Yellow wire - Motor A direction 2
IN3 = 13    # Blue wire - Motor B direction 1
IN4 = 15    # Green wire - Motor B direction 2
ENA = 33    # Purple wire - Motor A speed (PWM)
ENB = 32    # White wire - Motor B speed (PWM)

# Set all motor control pins as output and set initial state to LOW
pins = [IN1, IN2, IN3, IN4, ENA, ENB]
for pin in pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# Create PWM control for motor speed on ENA and ENB
pwm_left = GPIO.PWM(ENA, 1000)   # 1 KHz frequency for Motor A
pwm_right = GPIO.PWM(ENB, 1000)  # 1 KHz frequency for Motor B

pwm_left.start(0)   # Start with 0% duty cycle (stopped)
pwm_right.start(0)

# Move both motors forward
def move_forward():
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_left.ChangeDutyCycle(70)   # Set Motor A speed
    pwm_right.ChangeDutyCycle(70)  # Set Motor B speed

# Stop all motor movement
def stop_all():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    pwm_left.ChangeDutyCycle(0)
    pwm_right.ChangeDutyCycle(0)

# Run a quick test to move forward for 2 seconds
try:
    print("Moving forward")
    move_forward()
    time.sleep(2)
    print("Stopping")
    stop_all()
finally:
    # Stop PWM and clean up GPIO configuration on exit
    pwm_left.stop()
    pwm_right.stop()
    GPIO.cleanup()
