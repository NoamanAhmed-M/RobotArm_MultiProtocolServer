import socket
import threading
import asyncio
import websockets
import json
import numpy as np

class ChatServer:
    def __init__(self, tcp_host='0.0.0.0', tcp_port=5555, ws_host='0.0.0.0', ws_port=8765):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.ws_host = ws_host
        self.ws_port = ws_port

        self.tcp_clients = {}  # {socket: name}
        self.ws_clients = {}   # {websocket: name}
        
        self.routing_rules = {
            "client1": ["client2", "client3"],
            "client2": ["client1"],
            "admin": ["*"],
        }

        self.tcp_lock = threading.Lock()
        self.ws_lock = threading.Lock()

    def start(self):
        tcp_thread = threading.Thread(target=self.start_tcp_server, daemon=True)
        tcp_thread.start()
        asyncio.run(self.start_websocket_server())

    def start_tcp_server(self):
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
                data = client_socket.recv(4096)
                if not data:
                    break

                try:
                    message_obj = json.loads(data.decode('utf-8'))
                except Exception as e:
                    print(f"Error decoding message from {name}: {e}")
                    continue

                print(f"TCP Message from {name}: {message_obj}")
                self.route_tcp_message(message_obj, sender_name=name, sender_socket=client_socket)

        except Exception as e:
            print(f"TCP client error with {client_address}: {e}")
        finally:
            with self.tcp_lock:
                self.tcp_clients.pop(client_socket, None)
            client_socket.close()
            print(f"TCP client {name or client_address} disconnected.")

    async def start_websocket_server(self):
        print(f"WebSocket Server starting on {self.ws_host}:{self.ws_port}")
        async with websockets.serve(self.handle_websocket_client, self.ws_host, self.ws_port):
            print(f"WebSocket Server started on {self.ws_host}:{self.ws_port}")
            await asyncio.Future()

    async def handle_websocket_client(self, websocket, path):
        name = None
        try:
            name = await websocket.recv()
            with self.ws_lock:
                self.ws_clients[websocket] = name

            print(f"New WebSocket client: {name}")

            async for message in websocket:
                try:
                    message_obj = json.loads(message)
                except Exception as e:
                    print(f"WebSocket message decode error from {name}: {e}")
                    continue

                print(f"WebSocket Message from {name}: {message_obj}")
                await self.route_ws_message(message_obj, sender_name=name, sender_websocket=websocket)

        except websockets.exceptions.ConnectionClosed:
            print(f"WebSocket client {name} disconnected")
        except Exception as e:
            print(f"WebSocket client error: {e}")
        finally:
            with self.ws_lock:
                self.ws_clients.pop(websocket, None)

    def get_target_recipients(self, sender_name):
        if sender_name not in self.routing_rules:
            return []
        recipients = self.routing_rules[sender_name]
        return recipients if "*" not in recipients else ["*"]

    def route_tcp_message(self, message_obj, sender_name, sender_socket):
        targets = self.get_target_recipients(sender_name)

        with self.tcp_lock:
            for client_socket, client_name in list(self.tcp_clients.items()):
                if client_socket == sender_socket:
                    continue
                if "*" in targets or client_name in targets:
                    try:
                        message_obj['sender'] = sender_name
                        client_socket.send(json.dumps(message_obj).encode('utf-8'))
                    except:
                        self.tcp_clients.pop(client_socket, None)

    async def route_ws_message(self, message_obj, sender_name, sender_websocket):
        targets = self.get_target_recipients(sender_name)

        with self.ws_lock:
            for ws, client_name in list(self.ws_clients.items()):
                if ws == sender_websocket:
                    continue
                if "*" in targets or client_name in targets:
                    try:
                        message_obj['sender'] = sender_name
                        await ws.send(json.dumps(message_obj))
                    except:
                        self.ws_clients.pop(ws, None)

def main():
    server = ChatServer()
    server.start()

if __name__ == "__main__":
    main()
