import socket
import threading

def receive_messages(client_socket):
    """Continuously receive messages from the server."""
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if message:
                print(f"\n{message}")
            else:
                break
        except:
            print("Disconnected from server.")
            break

def start_client(host, port):
    """Start the TCP client."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    # Send the client name first
    name = "RobotArm"
    client_socket.send(name.encode('utf-8'))

    # Start a thread to listen for incoming messages
    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,), daemon=True)
    receive_thread.start()

    # Continuously send messages
    while True:
        message = input()
        if message.lower() == "exit":
            break
        client_socket.send(message.encode('utf-8'))

    client_socket.close()

if __name__ == "__main__":
    start_client('192.168.146.136', 5555)
