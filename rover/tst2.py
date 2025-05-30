sudo apt install python3-gpiozero
#!/usr/bin/env python3

from gpiozero import PWMOutputDevice, OutputDevice
import time

# BCM pin numbers
ENA = PWMOutputDevice(19)       # Pin 33 - software PWM
IN1 = OutputDevice(25)          # Pin 22
IN2 = OutputDevice(27)          # Pin 13

try:
    print("FORWARD at 75%")
    IN1.on()
    IN2.off()
    ENA.value = 0.75
    time.sleep(2)

    print("STOP")
    ENA.value = 0
    IN1.off()
    IN2.off()
    time.sleep(1)

    print("BACKWARD at 50%")
    IN1.off()
    IN2.on()
    ENA.value = 0.5
    time.sleep(2)

    print("STOP")
    ENA.value = 0
    IN1.off()
    IN2.off()

finally:
    ENA.close()
    IN1.close()
    IN2.close()
