import socket
import json
import threading
import time

SERVER_IP = '172.20.10.5'     # 🔁 Replace with the actual server IP
SERVER_PORT = 5555               # Must match your TCP server port
CLIENT_NAME = "RobotArm"         # 👈 Client identifier

def receive_messages(sock):
    """Receive and handle messages from the server"""
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                break
            message = json.loads(data.decode('utf-8'))
            print(f"[SERVER -> RobotArm] {message}")

            # Optional: respond to commands
            if message.get("type") == "command":
                if message.get("value") == True:
                    print("[RobotArm] Received ON command")
                else:
                    print("[RobotArm] Received OFF command")

        except Exception as e:
            print(f"[ERROR] Receiving failed: {e}")
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
            print("[RobotArm -> Server] Sent status update")
            time.sleep(5)
        except Exception as e:
            print(f"[ERROR] Sending failed: {e}")
            break

def main():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_IP, SERVER_PORT))
        print("[RobotArm] Connected to server")

        # Step 1: Send the name as identifier
        sock.send((CLIENT_NAME + "\n").encode('utf-8'))

        # Step 2: Start receiver and sender
        threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()
        send_status_messages(sock)

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
