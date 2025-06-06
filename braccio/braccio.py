import tkinter as tk
from tkinter import ttk
import threading
import time
import serial


class TS3215Controller:
    def __init__(self, port='/dev/ttyTHS1', baudrate=115200):
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
        if self.ser and self.ser.is_open:
            self.ser.write(packet)


class ServoGUI(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.title("Controllo Braccio Robotico - TS3215")
        self.geometry("400x350")
        self.controller = controller

        self.positions = {i: 1500 for i in range(1, 6)}
        self.selected_servo = 1

        self.create_widgets()

        # Connetti seriale in un thread per non bloccare GUI
        threading.Thread(target=self.controller.connect, daemon=True).start()

    def create_widgets(self):
        self.servo_label = ttk.Label(self, text=f"Servo selezionato: {self.selected_servo}", font=("Arial", 14))
        self.servo_label.pack(pady=10)

        # Slider per servo selezionato
        self.position_slider = ttk.Scale(self, from_=500, to=2500, orient="horizontal",
                                         command=self.on_slider_change)
        self.position_slider.set(self.positions[self.selected_servo])
        self.position_slider.pack(fill="x", padx=20)

        # Label posizione
        self.position_value_label = ttk.Label(self, text=f"Posizione: {self.positions[self.selected_servo]} µs")
        self.position_value_label.pack(pady=5)

        # Bottoni per cambiare servo
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Servo -", command=self.prev_servo).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Servo +", command=self.next_servo).grid(row=0, column=1, padx=5)

        # Bottoni per spostare servo
        move_frame = ttk.Frame(self)
        move_frame.pack(pady=10)

        ttk.Button(move_frame, text="←", command=lambda: self.move_servo(-20)).grid(row=0, column=0, padx=5)
        ttk.Button(move_frame, text="→", command=lambda: self.move_servo(20)).grid(row=0, column=1, padx=5)

        # Bottone esci
        ttk.Button(self, text="Esci", command=self.on_exit).pack(pady=20)

    def prev_servo(self):
        if self.selected_servo > 1:
            self.selected_servo -= 1
            self.update_servo_selection()

    def next_servo(self):
        if self.selected_servo < 5:
            self.selected_servo += 1
            self.update_servo_selection()

    def update_servo_selection(self):
        self.servo_label.config(text=f"Servo selezionato: {self.selected_servo}")
        pos = self.positions[self.selected_servo]
        self.position_slider.set(pos)
        self.position_value_label.config(text=f"Posizione: {pos} µs")

    def move_servo(self, delta):
        pos = self.positions[self.selected_servo] + delta
        pos = max(500, min(2500, pos))
        self.positions[self.selected_servo] = pos
        self.position_slider.set(pos)
        self.position_value_label.config(text=f"Posizione: {pos} µs")
        self.controller.send_position(self.selected_servo, pos)

    def on_slider_change(self, event):
        pos = int(float(self.position_slider.get()))
        self.positions[self.selected_servo] = pos
        self.position_value_label.config(text=f"Posizione: {pos} µs")
        self.controller.send_position(self.selected_servo, pos)

    def on_exit(self):
        self.controller.disconnect()
        self.destroy()


if __name__ == "__main__":
    controller = TS3215Controller()
    app = ServoGUI(controller)
    app.mainloop()
