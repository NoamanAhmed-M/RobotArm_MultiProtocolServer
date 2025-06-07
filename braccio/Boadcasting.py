
import serial
import time

def move_servo(ser, servo_id, position_us=1500, time_ms=20):
    pos_val = int(position_us * 4)
    t_val = int(time_ms / 20)

    packet = bytearray([
        0x55, 0x55,
        servo_id,
        7,
        1,
        pos_val & 0xFF,
        (pos_val >> 8) & 0xFF,
        t_val & 0xFF,
        (t_val >> 8) & 0xFF
    ])
    ser.write(packet)
    ser.flush()

def scan_all_ids():
    try:
        ser = serial.Serial('/dev/ttyTHS1', 115200, timeout=0.1)
        print("[✓] Serial connected on /dev/ttyTHS1\n")

        for sid in range(0, 254):  # 0x00 to 0xFD
            print(f"[→] Trying ID: {sid}...", end=" ", flush=True)
            move_servo(ser, sid)
            time.sleep(0.15)
            print("✓ sent")

        ser.close()
        print("\n[✓] Scan complete. Watch for servo motion or LED blink.")

    except serial.SerialException as e:
        print(f"[!] Serial error: {e}")

if __name__ == "__main__":
    scan_all_ids()


