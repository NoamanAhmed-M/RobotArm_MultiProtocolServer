import socket
import threading

def receive_messages(client_socket):
    """Continuously receive messages from the Raspberry Pi server."""
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if message:
                print("\n{}".format(message))
            else:
                break
        except Exception as e:
            print("Disconnected from server. Error:", e)
            break

def start_client(host, port):
    """Start the TCP client on Jetson Nano."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, port))
        
        # Send the client name first - updated for Jetson Nano
        name = "JetsonNano"
        client_socket.send(name.encode('utf-8'))
        
        # Start a thread to listen for incoming messages
        receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
        receive_thread.daemon = True
        receive_thread.start()
        
        print(f"Connected to server at {host}:{port}")
        print("Type your messages and press Enter to send. Type 'exit' to quit.")
        
        # Continuously send messages
        while True:
            message = input()
            if message.lower() == "exit":
                break
            client_socket.send(message.encode('utf-8'))
            
    except ConnectionRefusedError:
        print(f"Connection refused. Make sure the server is running at {host}:{port}")
    except KeyboardInterrupt:
        print("\nClient interrupted. Closing connection.")
    finally:
        client_socket.close()

if __name__ == "__main__":
    # Update this to your Raspberry Pi's IP address
    raspberry_pi_ip = '172.20.10.5'  # Replace with your Raspberry Pi's actual IP
    port = 5555  # Make sure this matches the port your Raspberry Pi server is using
    
    start_client(raspberry_pi_ip, port)
