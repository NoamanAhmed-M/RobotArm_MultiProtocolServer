#!/usr/bin/env python3
"""
Controllo Braccio Robotico con 5 Servo TS3215 - CONTROLLO TASTIERA
Jetson Nano - Pin 8 (TX) - 5 Gradi di Libertà
"""

import serial
import time
import threading
import sys
import termios
import tty
from typing import Dict, List, Tuple


class KeyboardListener:
    """Classe per catturare input da tastiera in tempo reale"""

    def __init__(self):
        self.old_settings = None

    def __enter__(self):
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.cbreak(sys.stdin.fileno())
        return self

    def __exit__(self, type, value, traceback):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def get_key(self):
        """Ottiene un singolo carattere dalla tastiera"""
        return sys.stdin.read(1)


class TS3215Controller:
    """Controller per servo TS3215 tramite comunicazione seriale"""

    def __init__(self, port='/dev/ttyTHS1', baudrate=1000000):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_connected = False
        self.servo_positions = {1: 512, 2: 512, 3: 512, 4: 512, 5: 512}

        # Limiti sicurezza per ogni servo (min, max)
        self.servo_limits = {
            1: (100, 924),  # Base rotation
            2: (200, 824),  # Shoulder
            3: (150, 874),  # Elbow
            4: (100, 924),  # Wrist rotation
            5: (300, 724)  # Gripper
        }

        # Step di movimento per controllo fine
        self.movement_step = {
            'fine': 5,  # Movimento fine
            'normal': 20,  # Movimento normale
            'fast': 50  # Movimento veloce
        }

    def connect(self) -> bool:
        """Connette alla porta seriale"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1
            )

            if self.serial_conn.is_open:
                self.is_connected = True
                print(f"✓ Connesso a {self.port} @ {self.baudrate} baud")
                self.center_all_servos()
                return True
            else:
                print(f"✗ Errore apertura porta {self.port}")
                return False

        except Exception as e:
            print(f"✗ Errore connessione: {e}")
            return False

    def disconnect(self):
        """Disconnette dalla porta seriale"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.is_connected = False
            print("✓ Disconnesso")

    def _calculate_checksum(self, packet: List[int]) -> int:
        """Calcola checksum per pacchetto TS3215"""
        return (~sum(packet[2:])) & 0xFF

    def _send_command(self, servo_id: int, instruction: int, parameters: List[int]) -> bool:
        """Invia comando a servo specifico"""
        if not self.is_connected:
            return False

        length = len(parameters) + 2
        packet = [0xFF, 0xFF, servo_id, length, instruction] + parameters
        checksum = self._calculate_checksum(packet)
        packet.append(checksum)

        try:
            self.serial_conn.write(bytes(packet))
            time.sleep(0.002)
            return True
        except:
            return False

    def set_servo_position(self, servo_id: int, position: int, speed: int = 800) -> bool:
        """Imposta posizione servo"""
        if servo_id not in range(1, 6):
            return False

        # Controllo limiti di sicurezza
        min_pos, max_pos = self.servo_limits[servo_id]
        position = max(min_pos, min(max_pos, position))

        parameters = [
            0x2A,
            position & 0xFF,
            (position >> 8) & 0xFF,
            speed & 0xFF,
            (speed >> 8) & 0xFF
        ]

        success = self._send_command(servo_id, 0x03, parameters)

        if success:
            self.servo_positions[servo_id] = position

        return success

    def move_servo_relative(self, servo_id: int, step: int, speed: int = 800) -> bool:
        """Muove servo relativamente alla posizione corrente"""
        current_pos = self.servo_positions[servo_id]
        new_pos = current_pos + step
        return self.set_servo_position(servo_id, new_pos, speed)

    def center_all_servos(self, speed: int = 300):
        """Centra tutti i servo"""
        for servo_id in range(1, 6):
            self.set_servo_position(servo_id, 512, speed)
        time.sleep(1)

    def get_current_positions(self) -> Dict[int, int]:
        """Restituisce posizioni correnti"""
        return self.servo_positions.copy()


class KeyboardRobotController:
    """Controller braccio robotico con controllo tastiera"""

    def __init__(self):
        self.servo_controller = TS3215Controller()
        self.is_running = False
        self.current_servo = 1  # Servo attualmente selezionato
        self.movement_mode = 'normal'  # fine, normal, fast
        self.auto_speed = 800

        # Mappatura tasti
        self.key_mappings = {
            # Selezione servo
            '1': ('select_servo', 1),
            '2': ('select_servo', 2),
            '3': ('select_servo', 3),
            '4': ('select_servo', 4),
            '5': ('select_servo', 5),

            # Movimento servo corrente
            'a': ('move_servo', -1),  # Sinistra/Chiudi
            'd': ('move_servo', 1),  # Destra/Apri

            # Movimento multiplo
            'q': ('move_servo', 1, 1),  # Base sinistra
            'e': ('move_servo', -1, 1),  # Base destra
            'w': ('move_servo', 1, 2),  # Spalla su
            's': ('move_servo', -1, 2),  # Spalla giù
            'r': ('move_servo', 1, 3),  # Gomito su
            'f': ('move_servo', -1, 3),  # Gomito giù
            't': ('move_servo', 1, 4),  # Polso orario
            'g': ('move_servo', -1, 4),  # Polso antiorario
            'y': ('move_servo', 1, 5),  # Gripper apri
            'h': ('move_servo', -1, 5),  # Gripper chiudi

            # Modalità movimento
            'z': ('set_mode', 'fine'),
            'x': ('set_mode', 'normal'),
            'c': ('set_mode', 'fast'),

            # Comandi speciali
            ' ': ('center_all',),  # Spazio = centra tutto
            'p': ('save_position',),  # Salva posizione
            'l': ('load_position',),  # Carica posizione
            'i': ('show_info',),  # Mostra info
            '\x1b': ('quit',),  # ESC = esci
        }

        # Posizioni salvate
        self.saved_positions = {}

    def initialize(self) -> bool:
        """Inizializza il sistema"""
        print("🤖 CONTROLLO BRACCIO ROBOTICO - MODALITÀ TASTIERA")
        print("=" * 60)

        if self.servo_controller.connect():
            self.is_running = True
            self._show_controls()
            return True
        else:
            print("✗ Errore inizializzazione")
            return False

    def shutdown(self):
        """Spegne il sistema"""
        print("\n🔄 Spegnimento sistema...")
        if self.is_running:
            self.servo_controller.center_all_servos()
            time.sleep(1)
        self.servo_controller.disconnect()
        self.is_running = False
        print("✓ Sistema spento")

    def _show_controls(self):
        """Mostra controlli tastiera"""
        print("\n🎮 CONTROLLI TASTIERA:")
        print("-" * 60)
        print("SELEZIONE SERVO:")
        print("  1-5: Seleziona servo (1=Base, 2=Spalla, 3=Gomito, 4=Polso, 5=Gripper)")
        print()
        print("MOVIMENTO SERVO SELEZIONATO:")
        print("  A/D: Muovi servo corrente (←/→)")
        print()
        print("MOVIMENTO DIRETTO:")
        print("  Q/E: Base (←/→)      W/S: Spalla (↑/↓)")
        print("  R/F: Gomito (↑/↓)    T/G: Polso (⟲/⟳)")
        print("  Y/H: Gripper (apri/chiudi)")
        print()
        print("MODALITÀ MOVIMENTO:")
        print("  Z: Fine (step=5)     X: Normale (step=20)     C: Veloce (step=50)")
        print()
        print("COMANDI SPECIALI:")
        print("  SPAZIO: Centra tutti    P: Salva posizione    L: Carica posizione")
        print("  I: Info sistema         ESC: Esci")
        print("-" * 60)

    def _update_display(self):
        """Aggiorna display informazioni"""
        # Pulisce schermo (solo le ultime righe)
        print(f"\r🎯 Servo: {self.current_servo} | Modalità: {self.movement_mode.upper()} | ", end="")

        positions = self.servo_controller.get_current_positions()
        servo_names = ["", "Base", "Spalla", "Gomito", "Polso", "Gripper"]

        pos_str = " | ".join([f"{servo_names[i]}={positions[i]:3d}" for i in range(1, 6)])
        print(f"{pos_str}", end="", flush=True)

    def _handle_key(self, key: str):
        """Gestisce pressione tasto"""
        if key not in self.key_mappings:
            return

        command = self.key_mappings[key]
        action = command[0]

        if action == 'select_servo':
            self.current_servo = command[1]
            print(f"\n🎯 Servo {self.current_servo} selezionato")

        elif action == 'move_servo':
            if len(command) == 2:
                # Movimento servo corrente
                direction = command[1]
                servo_id = self.current_servo
            else:
                # Movimento servo specifico
                direction = command[1]
                servo_id = command[2]

            step = self.servo_controller.movement_step[self.movement_mode]
            movement = step * direction

            self.servo_controller.move_servo_relative(servo_id, movement, self.auto_speed)

        elif action == 'set_mode':
            self.movement_mode = command[1]
            print(f"\n⚡ Modalità: {self.movement_mode.upper()}")

        elif action == 'center_all':
            print(f"\n🎯 Centratura servo...")
            self.servo_controller.center_all_servos()

        elif action == 'save_position':
            self._save_current_position()

        elif action == 'load_position':
            self._load_saved_position()

        elif action == 'show_info':
            self._show_detailed_info()

        elif action == 'quit':
            self.is_running = False
            print(f"\n👋 Uscita...")

    def _save_current_position(self):
        """Salva posizione corrente"""
        positions = self.servo_controller.get_current_positions()
        timestamp = time.strftime("%H:%M:%S")
        position_name = f"pos_{len(self.saved_positions) + 1}"

        self.saved_positions[position_name] = {
            'positions': positions.copy(),
            'timestamp': timestamp
        }

        print(f"\n💾 Posizione salvata come '{position_name}' alle {timestamp}")

    def _load_saved_position(self):
        """Carica posizione salvata"""
        if not self.saved_positions:
            print(f"\n❌ Nessuna posizione salvata")
            return

        print(f"\n📂 Posizioni salvate:")
        for i, (name, data) in enumerate(self.saved_positions.items(), 1):
            print(f"  {i}. {name} - {data['timestamp']}")

        # Per semplicità, carica l'ultima posizione salvata
        last_position = list(self.saved_positions.values())[-1]
        positions = last_position['positions']

        print(f"📥 Caricamento ultima posizione...")
        for servo_id, position in positions.items():
            self.servo_controller.set_servo_position(servo_id, position, 400)

    def _show_detailed_info(self):
        """Mostra informazioni dettagliate"""
        print(f"\n" + "=" * 50)
        print(f"📊 INFORMAZIONI SISTEMA")
        print(f"=" * 50)

        positions = self.servo_controller.get_current_positions()
        limits = self.servo_controller.servo_limits
        servo_names = {1: "Base", 2: "Spalla", 3: "Gomito", 4: "Polso", 5: "Gripper"}

        for servo_id in range(1, 6):
            name = servo_names[servo_id]
            pos = positions[servo_id]
            min_pos, max_pos = limits[servo_id]
            percentage = ((pos - min_pos) / (max_pos - min_pos)) * 100

            # Barra di posizione
            bar_length = 20
            filled = int((percentage / 100) * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)

            print(f"Servo {servo_id} ({name:8}): {pos:3d} [{bar}] {percentage:5.1f}%")

        print(f"\nModalità movimento: {self.movement_mode.upper()}")
        print(f"Step corrente: {self.servo_controller.movement_step[self.movement_mode]}")
        print(f"Posizioni salvate: {len(self.saved_positions)}")
        print(f"=" * 50)

    def start_keyboard_control(self):
        """Avvia controllo tastiera"""
        print(f"\n🚀 Modalità controllo tastiera attiva!")
        print(f"Premi 'I' per informazioni, ESC per uscire\n")

        with KeyboardListener() as listener:
            while self.is_running:
                try:
                    self._update_display()
                    key = listener.get_key()

                    if key:
                        self._handle_key(key.lower())

                    time.sleep(0.05)  # Piccola pausa per evitare sovraccarico CPU

                except KeyboardInterrupt:
                    print(f"\n🛑 Interruzione da tastiera")
                    break
                except Exception as e:
                    print(f"\n❌ Errore: {e}")
                    break

    def run(self):
        """Esegue il controller"""
        try:
            if self.initialize():
                self.start_keyboard_control()
        except Exception as e:
            print(f"\n❌ Errore: {e}")
        finally:
            self.shutdown()


def main():
    """Funzione principale"""
    print("🤖 Avvio controllo braccio robotico...")

    controller = KeyboardRobotController()
    controller.run()


if __name__ == "__main__":
    main()
