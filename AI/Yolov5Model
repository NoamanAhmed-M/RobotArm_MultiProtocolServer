sudo usermod -a -G dialout $USER

sudo gedit /etc/udev/rules.d/99-gpio.rules
SUBSYSTEM=="gpio*", PROGRAM="/bin/sh -c 'chown -R root:gpio /sys/class/gpio/ && chmod -R 770 /sys/class/gpio/'"
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo reboot
---------------
import Jetson.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)
GPIO.output(18, GPIO.HIGH)
GPIO.cleanup()
