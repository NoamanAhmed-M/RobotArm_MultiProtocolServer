#!/usr/bin/env python3
import sys
import termios
import tty
import select
import serial
import time

SERVO_IDS = [1, 2, 3, 4, 5]

class TS3215Controller:
    def _init_(self, port='/dev/ttyTHS1', baudrate=1000000):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.positions = {sid: 512 for sid in SERVO_IDS}
        self.limits = {
            1: (100, 924),  # Base
            2: (200, 824),  # Spalla
            3: (150, 874),  # Gomito
            4: (100, 924),  # Polso
            5: (300, 724),  # Gripper
        }

    def connect(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=0.1)
            if self.serial_conn.is_open:
                print(f"✓ Connesso a {self.port}")
                return True
        except Exception as e:
            print(f"Errore connessione: {e}")
        return False

    def disconnect(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

    def _checksum(self, pkt):
        return (~sum(pkt[2:])) & 0xFF

    def send_command(self, servo_id, position, speed=800):
        position = max(self.limits[servo_id][0], min(self.limits[servo_id][1], position))
        self.positions[servo_id] = position
        params = [
            0x2A,
            position & 0xFF,
            (position >> 8) & 0xFF,
            speed & 0xFF,
            (speed >> 8) & 0xFF,
        ]
        pkt = [0xFF, 0xFF, servo_id, len(params)+2, 0x03] + params
        pkt.append(self._checksum(pkt))
        self.serial_conn.write(bytes(pkt))
        time.sleep(0.005)

    def move_relative(self, servo_id, delta, speed=800):
        new_pos = self.positions[servo_id] + delta
        self.send_command(servo_id, new_pos, speed)

    def center_all(self):
        for sid in SERVO_IDS:
            self.send_command(sid, 512, 300)


class KeyboardRobotController:
    def _init_(self):
        self.servo = TS3215Controller()
        self.current_servo = 1
        self.step = 20
        self.running = True

    def print_controls(self):
        print("\n--- COMANDI ---")
        print("1-5: seleziona servo")
        print("A/D: muovi servo corrente")
        print("Z/X/C: step = 5 / 20 / 50")
        print("SPACE: centra tutti")
        print("ESC: esci\n")

    def get_key(self, timeout=0.1):
        dr, _, _ = select.select([sys.stdin], [], [], timeout)
        if dr:
            return sys.stdin.read(1)
        return None

    def run(self):
        if not self.servo.connect():
            print("Errore connessione seriale.")
            return

        self.print_controls()
        self.servo.center_all()

        old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

        try:
            while self.running:
                key = self.get_key()
                if key:
                    key = key.lower()
                    if key in '12345':
                        self.current_servo = int(key)
                        print(f"> Servo selezionato: {self.current_servo}")
                    elif key == 'a':
                        self.servo.move_relative(self.current_servo, -self.step)
                    elif key == 'd':
                        self.servo.move_relative(self.current_servo, self.step)
                    elif key == 'z':
                        self.step = 5
                        print("✓ Modalità FINE")
                    elif key == 'x':
                        self.step = 20
                        print("✓ Modalità NORMALE")
                    elif key == 'c':
                        self.step = 50
                        print("✓ Modalità VELOCE")
                    elif key == ' ':
                        print("✓ Centratura servomotori...")
                        self.servo.center_all()
                    elif key == '\x1b':  # ESC
                        print("👋 Uscita")
                        self.running = False

                time.sleep(0.05)

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self.servo.disconnect()


if _name_ == "_main_":
    print("🤖 Avvio controllo braccio robotico (TS3215)")
    controller = KeyboardRobotController()
    controller.run()
