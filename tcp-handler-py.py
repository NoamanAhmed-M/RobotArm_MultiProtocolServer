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
                threading.Thread(target=self.handle_tcp_client, 
                                args=(client_socket, client_address), 
                                daemon=True).start()

    def handle_tcp_client(self, client_socket, client_address):
        """Handle individual TCP client connections"""
        name = None
        try:
            name = client_socket.recv(1024).decode('utf-8').strip()
            if not name:
                return

            with self.server.tcp_lock:
                self.server.tcp_clients[client_socket] = name
            print(f"[TCP] {name} connected from {client_address}")

            while True:
                data = client_socket.recv(4096)
                if not data:
                    break

                message_obj = json.loads(data.decode('utf-8'))
                print(f"[TCP] Message from {name}: {message_obj}")
                self.route_tcp_message(message_obj, name, client_socket)

        except Exception as e:
            print(f"[TCP Error] {e}")
        finally:
            with self.server.tcp_lock:
                self.server.tcp_clients.pop(client_socket, None)
            client_socket.close()
            print(f"[TCP] {name or client_address} disconnected")
    
    def route_tcp_message(self, message_obj, sender_name, sender_socket):
        """Route messages from TCP clients to appropriate destinations"""
        targets = self.server.get_target_recipients(sender_name)
        with self.server.tcp_lock:
            for client_socket, client_name in list(self.server.tcp_clients.items()):
                if client_socket == sender_socket:
                    continue
                if "*" in targets or client_name in targets:
                    try:
                        message_obj["sender"] = sender_name
                        client_socket.send(json.dumps(message_obj).encode("utf-8"))
                    except:
                        self.server.tcp_clients.pop(client_socket, None)
