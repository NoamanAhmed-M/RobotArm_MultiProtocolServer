import serial
import struct
import time
import keyboard


class TS3215Controller:
    def _init_(self, port='/dev/ttyTHS1', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            print(f"[✓] Connesso alla porta {self.port} @ {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"[!] Errore apertura porta seriale: {e}")
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[i] Porta seriale chiusa.")

    def send_position(self, servo_id, position, time_ms=20):
        # Converte posizione (500-2500 µs) in unità (0.25 µs) → 2000-10000
        pos_val = int(position * 4)
        t_val = int(time_ms / 20)

        packet = bytearray([
            0x55, 0x55,             # Header
            servo_id,              # ID
            7,                     # Lunghezza (comando + dati)
            1,                     # Istruzione: posizione
            pos_val & 0xFF,        # Posizione Low
            (pos_val >> 8) & 0xFF, # Posizione High
            t_val & 0xFF,          # Tempo Low
            (t_val >> 8) & 0xFF    # Tempo High
        ])
        self.ser.write(packet)

    def move_all_servos(self, positions: dict, time_ms=200):
        for servo_id, pos in positions.items():
            self.send_position(servo_id, pos, time_ms)
            time.sleep(0.01)  # Ritardo minimo per evitare sovrapposizioni


class KeyboardRobotController:
    def _init_(self):
        self.servo = TS3215Controller('/dev/ttyTHS1')
        self.selected_servo = 1
        self.positions = {
            1: 1500,
            2: 1500,
            3: 1500,
            4: 1500,
            5: 1500
        }

    def run(self):
        print("🤖 Avvio controllo braccio robotico (TS3215)")
        print(" - Usa freccia SU/GIÙ per cambiare servo (1-5)")
        print(" - Usa freccia SINISTRA/DESTRA per muovere il servo")
        print(" - ESC per uscire")

        if not self.servo.connect():
            return

        try:
            while True:
                if keyboard.is_pressed('up'):
                    self.selected_servo = min(self.selected_servo + 1, 5)
                    print(f"Selezionato servo: {self.selected_servo}")
                    time.sleep(0.2)

                elif keyboard.is_pressed('down'):
                    self.selected_servo = max(self.selected_servo - 1, 1)
                    print(f"Selezionato servo: {self.selected_servo}")
                    time.sleep(0.2)

                elif keyboard.is_pressed('left'):
                    self.positions[self.selected_servo] = max(500, self.positions[self.selected_servo] - 20)
                    self.servo.send_position(self.selected_servo, self.positions[self.selected_servo])
                    print(f"Servo {self.selected_servo} → {self.positions[self.selected_servo]}")
                    time.sleep(0.1)

                elif keyboard.is_pressed('right'):
                    self.positions[self.selected_servo] = min(2500, self.positions[self.selected_servo] + 20)
                    self.servo.send_position(self.selected_servo, self.positions[self.selected_servo])
                    print(f"Servo {self.selected_servo} → {self.positions[self.selected_servo]}")
                    time.sleep(0.1)

                elif keyboard.is_pressed('esc'):
                    print("🛑 Uscita dal controllo braccio.")
                    break

                time.sleep(0.01)

        finally:
            self.servo.disconnect()


if _name_ == "_main_":
    controller = KeyboardRobotController()
    controller.run()
