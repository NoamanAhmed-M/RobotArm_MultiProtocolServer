import threading
import time
from tcp_client.tcp_handler import start_tcp_client
from udp_client.udp_camera import start_udp_camera

if __name__ == "__main__":
    print("🚀 Starting Jetson Nano Client...")

    tcp_thread = threading.Thread(target=start_tcp_client, daemon=True)
    udp_thread = threading.Thread(target=start_udp_camera, daemon=True)

    tcp_thread.start()
    udp_thread.start()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Main] 🔌 Exiting program")
            break
