import socket
import json
import threading
import time

SERVER_IP = '172.20.10.5'   # Replace with your server's IP
SERVER_PORT = 5555
CLIENT_NAME = "RobotArm"

RECONNECT_DELAY = 5  # seconds

def receive_messages(sock):
    """Receive and handle messages from the server"""
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print("[RobotArm] ❌ Server closed connection")
                break

            message = json.loads(data.decode('utf-8'))
            print(f"[SERVER -> RobotArm] {message}")

            if message.get("type") == "command":
                if message.get("value") == True:
                    print("[RobotArm] ✅ Received ON command")
                else:
                    print("[RobotArm] ✅ Received OFF command")

        except Exception as e:
            print(f"[RobotArm] ❌ Receiving failed: {e}")
            break

def send_status_messages(sock):
    """Periodically send status update to server"""
    while True:
        try:
            message = {
                "type": "status",
                "msg": "Arm ready",
                "position": [10, 20, 30]
            }
            sock.send(json.dumps(message).encode('utf-8'))
            print("[RobotArm -> Server] ✅ Sent status update")
            time.sleep(5)
        except Exception as e:
            print(f"[RobotArm] ❌ Sending failed: {e}")
            break

def start_client():
    while True:
        try:
            print(f"[RobotArm] 🔌 Connecting to {SERVER_IP}:{SERVER_PORT}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_IP, SERVER_PORT))
            print("[RobotArm] ✅ Connected to server")

            # Step 1: Send identifier name
            sock.send((CLIENT_NAME + "\n").encode('utf-8'))

            # Step 2: Start receiving in background
            recv_thread = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
            recv_thread.start()

            # Step 3: Start sending in main thread
            send_status_messages(sock)

        except Exception as e:
            print(f"[RobotArm] ❌ Connection failed: {e}")
        
        finally:
            try:
                sock.close()
            except:
                pass

            print(f"[RobotArm] 🔁 Reconnecting in {RECONNECT_DELAY} seconds...")
            time.sleep(RECONNECT_DELAY)

if __name__ == "__main__":
    start_client()
