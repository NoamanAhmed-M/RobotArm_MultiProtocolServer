import socket
import json
import threading
import time

SERVER_IP = '172.20.10.5'     # Replace with actual server IP
SERVER_PORT = 5555               # Match with server's TCP port
CLIENT_NAME = "RobotArm"

def receive_messages(sock):
    """Receive and print messages from the server."""
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                break
            message = json.loads(data.decode('utf-8'))
            print(f"[SERVER] {message}")
        except Exception as e:
            print(f"[ERROR] Receiving failed: {e}")
            break

def send_messages(sock):
    """Send messages to the server."""
    while True:
        try:
            # Customize this JSON message for actual use
            message = {
                "type": "status_update",
                "status": "ready",
                "position": [10, 20, 30]
            }
            sock.send(json.dumps(message).encode('utf-8'))
            print("[CLIENT] Sent message:", message)
            time.sleep(5)
        except Exception as e:
            print(f"[ERROR] Sending failed: {e}")
            break

def main():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_IP, SERVER_PORT))
        print("[CLIENT] Connected to server")

        # Step 1: Send identifier
        sock.send((CLIENT_NAME + "\n").encode('utf-8'))

        # Step 2: Start threads
        threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()
        send_messages(sock)

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
