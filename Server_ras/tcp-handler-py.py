import socket
import threading
import json

class TCPHandler:
    def __init__(self, server):
        self.server = server

    def start_tcp_server(self):
        """Start TCP server and listen for connections"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.server.tcp_host, self.server.tcp_port))
            server_socket.listen()
            print(f"[TCP] Server started on {self.server.tcp_host}:{self.server.tcp_port}")

            while True:
                client_socket, client_address = server_socket.accept()
                threading.Thread(
                    target=self.handle_tcp_client,
                    args=(client_socket, client_address),
                    daemon=True
                ).start()

    def handle_tcp_client(self, client_socket, client_address):
        """Handle individual TCP client connections"""
        name = None
        try:
            # First message is the client name
            name = client_socket.recv(1024).decode('utf-8').strip()
            if not name:
                print(f"[TCP] ❌ Empty client name from {client_address}")
                return

            with self.server.tcp_lock:
                self.server.tcp_clients[client_socket] = name
            print(f"[TCP] ✅ {name} connected from {client_address}")

            # Listen for messages
            while True:
                data = client_socket.recv(4096)
                if not data:
                    print(f"[TCP] ❌ No data from {name}, disconnecting.")
                    break

                try:
                    message_obj = json.loads(data.decode('utf-8'))
                    print(f"[TCP] 📥 Message from {name}: {message_obj}")
                    # Route message via central router
                    self.server.router.route(message_obj, name, sender_type="tcp")
                except json.JSONDecodeError as e:
                    print(f"[TCP] ❌ Invalid JSON from {name}: {e}")

        except Exception as e:
            print(f"[TCP] ❌ Error with {name or client_address}: {e}")
        finally:
            with self.server.tcp_lock:
                self.server.tcp_clients.pop(client_socket, None)
            try:
                client_socket.close()
            except:
                pass
            print(f"[TCP] 🔌 {name or client_address} disconnected")
