import socket
import threading
import asyncio
import websockets

class ChatServer:
    def __init__(self, tcp_host='0.0.0.0', tcp_port=5555, ws_host='0.0.0.0', ws_port=8765):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.ws_host = ws_host
        self.ws_port = ws_port

        self.tcp_clients = {}  # {socket: name}
        self.ws_clients = {}   # {websocket: name}

        self.tcp_lock = threading.Lock()
        self.ws_lock = threading.Lock()

    def start(self):
        # Start TCP server in a separate thread
        tcp_thread = threading.Thread(target=self.start_tcp_server, daemon=True)
        tcp_thread.start()

        # Start WebSocket server using asyncio
        asyncio.run(self.start_websocket_server())

    def start_tcp_server(self):
        """Start TCP server"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.tcp_host, self.tcp_port))
            server_socket.listen()
            print(f"TCP Server started on {self.tcp_host}:{self.tcp_port}")

            while True:
                try:
                    client_socket, client_address = server_socket.accept()
                    threading.Thread(
                        target=self.handle_tcp_client,
                        args=(client_socket, client_address),
                        daemon=True
                    ).start()
                except Exception as e:
                    print(f"TCP server error: {e}")

    def handle_tcp_client(self, client_socket, client_address):
        """Handle TCP client"""
        name = None
        try:
            name = client_socket.recv(1024).decode('utf-8').strip()
            if not name:
                client_socket.close()
                return

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
            with self.tcp_lock:
                self.tcp_clients.pop(client_socket, None)
            client_socket.close()
            print(f"TCP client {name or client_address} disconnected.")

    async def start_websocket_server(self):
        """Start WebSocket server"""
        print(f"WebSocket Server starting on {self.ws_host}:{self.ws_port}")
        async with websockets.serve(self.handle_websocket_client, self.ws_host, self.ws_port):
            print(f"WebSocket Server started on {self.ws_host}:{self.ws_port}")
            await asyncio.Future()  # run forever

    async def handle_websocket_client(self, websocket, path):
        """Handle WebSocket client"""
        name = None
        try:
            name = await websocket.recv()
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
            with self.ws_lock:
                self.ws_clients.pop(websocket, None)

    def broadcast_tcp_message(self, message, sender_name, exclude_socket=None):
        """Send TCP message to all clients except sender"""
        with self.tcp_lock:
            for client_socket in list(self.tcp_clients.keys()):
                if client_socket != exclude_socket:
                    try:
                        client_socket.send(f"{sender_name}: {message}".encode('utf-8'))
                    except:
                        self.tcp_clients.pop(client_socket, None)

    async def broadcast_ws_message(self, message, sender_name, exclude_websocket=None):
        """Send WS message to all clients except sender"""
        with self.ws_lock:
            for ws in list(self.ws_clients.keys()):
                if ws != exclude_websocket:
                    try:
                        await ws.send(f"{sender_name}: {message}")
                    except:
                        self.ws_clients.pop(ws, None)

def main():
    server = ChatServer()
    server.start()

if __name__ == "__main__":
    main()
