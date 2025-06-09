import socket
import threading
import json
import sys
from data_handler import DataHandler

class TCPHandler:
    def __init__(self, server):
        self.server = server
        
        # Handle different Python versions for JSON exception
        if sys.version_info >= (3, 5):
            self.json_decode_error = json.JSONDecodeError
        else:
            self.json_decode_error = ValueError  # In older Python versions, json uses ValueError
    
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
    
    def parse_multiple_json(self, data_str):
        """Parse multiple JSON objects from a single string"""
        messages = []
        decoder = json.JSONDecoder()
        idx = 0
        
        while idx < len(data_str):
            data_str = data_str[idx:].lstrip()  # Remove leading whitespace
            if not data_str:
                break
                
            try:
                message_obj, end_idx = decoder.raw_decode(data_str)
                messages.append(message_obj)
                idx += end_idx
            except self.json_decode_error as e:
                # If we can't parse more JSON, break
                if not messages:  # If no messages parsed yet, it's a real error
                    raise e
                break
                
        return messages
    
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
                    data_str = data.decode('utf-8').strip()
                    print(f"[TCP] Raw data from {name}: {data_str}")
                    
                    # Handle multiple JSON objects in one message
                    try:
                        messages = self.parse_multiple_json(data_str)
                        for message_obj in messages:
                            self.process_message(message_obj, name)
                    except:
                        # Fallback to single JSON parsing
                        message_obj = json.loads(data_str)
                        self.process_message(message_obj, name)
                        
                except self.json_decode_error as e:
                    print(f"[TCP] ❌ Invalid JSON from {name}: {e}")
                    print(f"[TCP] Raw data was: {data}")
                except UnicodeDecodeError as e:
                    print(f"[TCP] ❌ Unicode decode error from {name}: {e}")
                except Exception as e:
                    print(f"[TCP] ❌ Unexpected error processing data from {name}: {e}")
                    
        except Exception as e:
            print(f"[TCP] ❌ Error with {name or client_address}: {e}")
        finally:
            with self.server.tcp_lock:
                self.server.tcp_clients.pop(client_socket, None)
            try:
                client_socket.close()
            except:
                pass
            print(f"[TCP] {name or client_address} disconnected")
    
    def process_message(self, message_obj, name):
        """Process individual message objects"""
        print(f"[TCP] Message from {name}: {message_obj}")
        
        # Handle ESP32 sensor data
        if name == "ESP32_Sensor" and message_obj.get("type") == "sensor_data":
            sensor_value = message_obj.get("sensor_value", 0)
            threshold = message_obj.get("threshold", 500)
            success = self.server.data_handler.save_sensor_data(sensor_value, threshold)
            if success:
                print(f"[TCP] ✅ Sensor data saved: {sensor_value}")
            else:
                print(f"[TCP] ❌ Failed to save sensor data")
                
        # Handle ESP matrix data
        elif name == "ESP_Matrix" and message_obj.get("type") == "matrix":
            matrix = message_obj.get("matrix", [])
            success = self.server.data_handler.save_matrix_data(matrix)
            if success:
                print(f"[TCP] ✅ Matrix data saved")
            else:
                print(f"[TCP] ❌ Failed to save matrix data")
        
        # Handle client identification
        elif message_obj.get("type") == "client_id":
            client_id = message_obj.get("client_id", name)
            print(f"[TCP] Client {name} identified as: {client_id}")
            
        # Route other messages
        else:
            self.server.router.route(message_obj, name, sender_type="tcp")
