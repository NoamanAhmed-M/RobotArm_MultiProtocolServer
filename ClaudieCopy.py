# server code
# http_api.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import time
from urllib.parse import urlparse, parse_qs
import os

class DataAPIHandler(BaseHTTPRequestHandler):
    def __init__(self, data_handler, *args, **kwargs):
        print("Created HTTP_API_data handler")
        self.data_handler = data_handler
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for data"""
        print(f"HTTP GET request: {self.path}")
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        try:
            if path == '/api/sensor':
                print("api/sensor PATH")
                data = self.data_handler.get_sensor_data()
                print(f"Collected sensor data from file: {data}")
                self._send_json_response(data)
            
            elif path == '/api/matrix':
                print("api/matrix PATH")
                data = self.data_handler.get_matrix_data()
                print(f"Collected matrix data from file: {data}")
                self._send_json_response(data)
            
            elif path == '/api/sensor/history':
                print("api/sensor/history PATH")
                hours = int(query_params.get('hours', [24])[0])
                data = self.data_handler.get_sensor_history(hours)
                print(f"Collected sensor history: {len(data) if data else 0} entries")
                self._send_json_response(data)
            
            elif path == '/api/status':
                print("api/status PATH")
                status = {
                    "server": "running",
                    "timestamp": time.time(),
                    "files_exist": {
                        "sensor": self.data_handler.sensor_file.exists(),
                        "matrix": self.data_handler.matrix_file.exists()
                    }
                }
                self._send_json_response(status)
            
            else:
                print(f"Unknown path: {path}")
                self._send_error_response(404, "Endpoint not found")
        
        except Exception as e:
            print(f"[HTTP API] Error processing request: {e}")
            import traceback
            traceback.print_exc()
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def _send_json_response(self, data):
        """Send JSON response"""
        if data is None:
            print("Data is None, sending 404")
            self._send_error_response(404, "Data not found")
            return
        
        try:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            json_data = json.dumps(data, indent=2)
            self.wfile.write(json_data.encode('utf-8'))
            print(f"Sent JSON response: {len(json_data)} bytes")
            
        except Exception as e:
            print(f"Error sending JSON response: {e}")
            self._send_error_response(500, "Failed to send response")
    
    def _send_error_response(self, code, message):
        """Send error response"""
        try:
            self.send_response(code)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            error_data = {"error": message, "code": code}
            json_data = json.dumps(error_data)
            self.wfile.write(json_data.encode('utf-8'))
            print(f"Sent error response: {code} - {message}")
            
        except Exception as e:
            print(f"Error sending error response: {e}")

class HTTPAPIServer:
    def __init__(self, data_handler, host='0.0.0.0', port=8080):
        self.data_handler = data_handler
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
    
    def start(self):
        """Start HTTP API server in separate thread"""
        print(f"[HTTP API] Starting server on {self.host}:{self.port}")
        
        def run_server():
            try:
                # Create handler with data_handler bound
                def handler_factory(*args, **kwargs):
                    return DataAPIHandler(self.data_handler, *args, **kwargs)
                
                self.server = HTTPServer((self.host, self.port), handler_factory)
                print(f"[HTTP API] ✅ Server started on http://{self.host}:{self.port}")
                print(f"[HTTP API] Available endpoints:")
                print(f"  - GET /api/sensor - Current sensor data")
                print(f"  - GET /api/matrix - Current matrix data") 
                print(f"  - GET /api/sensor/history?hours=24 - Sensor history")
                print(f"  - GET /api/status - Server status")
                
                self.server.serve_forever()
                
            except Exception as e:
                print(f"[HTTP API] ❌ Server error: {e}")
                import traceback
                traceback.print_exc()
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        print(f"[HTTP API] Server thread started")
    
    def stop(self):
        """Stop HTTP API server"""
        if self.server:
            print("[HTTP API] Stopping server...")
            self.server.shutdown()
            self.server.server_close()
            print("[HTTP API] Server stopped")
