import serial
import time

def send_broadcast_position(position_us=1500, move_time_ms=20):
    try:
        # Open serial port
        ser = serial.Serial('/dev/ttyTHS1', 115200, timeout=0.1)
        print("[✓] Serial port /dev/ttyTHS1 opened")

        # Prepare TS3215 packet
        servo_id = 0xFE  # Broadcast ID
        pos_val = int(position_us * 4)
        t_val = int(move_time_ms / 20)

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

        print(f"[→] Sending position {position_us} µs to all servos...")
        ser.write(packet)
        ser.flush()
        print("[✓] Packet sent.")
        ser.close()

    except serial.SerialException as e:
        print(f"[!] Serial error: {e}")

if __name__ == "__main__":
    send_broadcast_position(position_us=1500)
    time.sleep(1)
    send_broadcast_position(position_us=1000)
    time.sleep(1)
    send_broadcast_position(position_us=2000)
