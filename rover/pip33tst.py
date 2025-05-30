import Jetson.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(19, GPIO.OUT)

print("Turning GPIO19 ON")
GPIO.output(19, GPIO.HIGH)
time.sleep(3)

print("Turning GPIO19 OFF")
GPIO.output(19, GPIO.LOW)
GPIO.cleanup()
sudo /opt/nvidia/jetson-io/jetson-io.py
sudo cat /sys/kernel/debug/gpio
