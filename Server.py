import socket
import threading
import asyncio
import websockets
import queue
import RPi.GPIO as GPIO
import time
import requests
import json

#First, if not installed, install this library (pip install requests)
# -------------------
#
# GPIO & Matrix Setup
# -------------------

# Set GPIO mode
#GPIO.setmode(GPIO.BCM)

# Define a 3x3 grid of GPIO pins for the sensors
# Adjust these GPIO numbers based on your wiring
#sensor_pins = [
#    [2, 3, 4],
#    [17, 27, 22],
#    [10, 9, 11]
#]

# Setup sensor pins as input
#for row in sensor_pins:
 #   for pin in row:
  #      GPIO.setup(pin, GPIO.IN)

# Create initial matrix (0 = empty, 1 = occupied)
matrix = [
    [0, 0, 0],
    [0, 0, 0],
    [0, 0, 0]
]

# Store previous state to detect changes
previous_matrix = [row.copy() for row in matrix]

# -------------------------
# Read sensor and update matrix
# -------------------------
#def update_matrix_from_sensors():
#    global matrix
 #   for i in range(3):
 #       for j in range(3):
            sensor_value = GPIO.input(sensor_pins[i][j])
            # Assuming: sensor_value == 1 when object is present
 #           matrix[i][j] = 1 if sensor_value else 0

# -------------------------
# Check if matrix changed
# -------------------------
def matrix_has_changed():
    for i in range(3):
        for j in range(3):
            if matrix[i][j] != previous_matrix[i][j]:
                return True
    return False

# -------------------------
# Send matrix to website server
# -------------------------
def send_matrix_to_server():
    url = "https://yourwebsite.com/api/update_matrix"  # Replace with real URL
    payload = {'matrix': matrix}
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        if response.status_code == 200:
            print("[✓] Matrix sent successfully.")
        else:
            print(f"[X] Server responded with code: {response.status_code}")
    except Exception as e:
        print(f"[X] Error sending matrix: {e}")

# -------------------------
# Main loop
# -------------------------
#try:
#    while True:
#        update_matrix_from_sensors()
#        if matrix_has_changed():
#            send_matrix_to_server()
            # Update previous_matrix after sending
#            for i in range(3):
                previous_matrix[i] = matrix[i].copy()
#        time.sleep(2)  # Check every 2 seconds

#except KeyboardInterrupt:
#    print("Exiting...")

#finally:
#    GPIO.cleanup()


class ChatServer:
    def __init__(self, tcp_host='0.0.0.0', tcp_port=5555, ws_host='0.0.0.0', ws_port=8765):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.ws_host = ws_host
        self.ws_port = ws_port
        
        # Client tracking
        self.tcp_clients = {}  # {socket: name}
        self.ws_clients = {}   # {websocket: name}
        
        # Synchronization
        self.tcp_lock = threading.Lock()
        self.ws_lock = threading.Lock()

    def start(self):
        """Start both TCP and WebSocket servers"""
        # Create event loop
        loop = asyncio.get_event_loop()
        
        # Start TCP server in a separate thread
        tcp_thread = threading.Thread(target=self.start_tcp_server, daemon=True)
        tcp_thread.start()
        
        # Prepare WebSocket server
        websocket_server = websockets.serve(
            self.handle_websocket_client, 
            self.ws_host, 
            self.ws_port
        )
        
        # Run WebSocket server
        loop.run_until_complete(websocket_server)
        print(f"WebSocket Server started on {self.ws_host}:{self.ws_port}")
        
        # Keep loop running
        loop.run_forever()

    def start_tcp_server(self):
        """Start TCP server to handle TCP client connections"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.tcp_host, self.tcp_port))
        server_socket.listen(5)
        print(f"TCP Server started on {self.tcp_host}:{self.tcp_port}")

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_tcp_client, 
                    args=(client_socket, client_address), 
                    daemon=True
                )
                client_thread.start()
            except Exception as e:
                print(f"TCP server error: {e}")

    def handle_tcp_client(self, client_socket, client_address):
        """Handle individual TCP client connections"""
        try:
            # Receive client name
            name = client_socket.recv(1024).decode('utf-8').strip()
            if not name:
                client_socket.close()
                return
            
            # Store client
            with self.tcp_lock:
                self.tcp_clients[client_socket] = name
            
            print(f"New TCP client: {name} ({client_address})")

            while True:
                message = client_socket.recv(1024).decode('utf-8').strip()
                if not message:
                    break
                
                print(f"TCP Message from {name}: {message}")
                self.broadcast_tcp_message(message, sender_name=name, exclude_socket=client_socket)
        
        except Exception as e:
            print(f"TCP client error with {client_address}: {e}")
        
        finally:
            # Clean up
            with self.tcp_lock:
                if client_socket in self.tcp_clients:
                    del self.tcp_clients[client_socket]
            client_socket.close()
            print(f"TCP client {name} disconnected.")

    async def handle_websocket_client(self, websocket, path):
        """Handle WebSocket client connections"""
        try:
            # Receive client name
            name = await websocket.recv()
            
            # Store WebSocket client
            with self.ws_lock:
                self.ws_clients[websocket] = name
            
            print(f"New WebSocket client: {name}")

            async for message in websocket:
                print(f"WebSocket Message from {name}: {message}")
                await self.broadcast_ws_message(message, sender_name=name, exclude_websocket=websocket)
        
        except websockets.exceptions.ConnectionClosed:
            print(f"WebSocket client {name} disconnected")
        
        except Exception as e:
            print(f"WebSocket client error: {e}")
        
        finally:
            # Clean up
            with self.ws_lock:
                if websocket in self.ws_clients:
                    del self.ws_clients[websocket]

    def broadcast_tcp_message(self, message, sender_name, exclude_socket=None):
        """Broadcast message to TCP clients"""
        with self.tcp_lock:
            for client_socket, client_name in list(self.tcp_clients.items()):
                if client_socket != exclude_socket:
                    try:
                        client_socket.send(f"{sender_name}: {message}".encode('utf-8'))
                    except:
                        # Remove failed clients
                        del self.tcp_clients[client_socket]

    async def broadcast_ws_message(self, message, sender_name, exclude_websocket=None):
        """Broadcast message to WebSocket clients"""
        with self.ws_lock:
            for ws, client_name in list(self.ws_clients.items()):
                if ws != exclude_websocket:
                    try:
                        await ws.send(f"{sender_name}: {message}")
                    except:
                        # Remove failed clients
                        del self.ws_clients[ws]

def main():
    server = ChatServer()
    server.start()

if __name__ == "__main__":
    main()
