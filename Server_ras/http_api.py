from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import time
from urllib.parse import urlparse, parse_qs
import os

class DataAPIHandler(BaseHTTPRequestHandler):
    def __init__(self, data_handler, *args, **kwargs):
        self.data_handler = data_handler
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for data"""
        print(f"[HTTP API] GET request: {self.path}")
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        try:
            if path == '/api/sensor':
                print("[HTTP API] Handling /api/sensor request")
                data = self.data_handler.get_sensor_data()
                print(f"[HTTP API] Sensor data retrieved: {data}")
                self._send_json_response(data)
            
            elif path == '/api/matrix':
                print("[HTTP API] Handling /api/matrix request")
                data = self.data_handler.get_matrix_data()
                print(f"[HTTP API] Matrix data retrieved: {data}")
                self._send_json_response(data)
            
            elif path == '/api/sensor/history':
                hours = int(query_params.get('hours', [24])[0])
                data = self.data_handler.get_sensor_history(hours)
                self._send_json_response(data)
            
            elif path == '/api/status':
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
                self._send_error_response(404, "Endpoint not found")
        
        except Exception as e:
            print(f"[HTTP API] Error handling request: {e}")
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        print("[HTTP API] CORS preflight request")
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def _send_json_response(self, data):
        """Send JSON response"""
        if data is None:
            print("[HTTP API] Data is None, sending 404")
            self._send_error_response(404, "Data not found")
            return
        
        print(f"[HTTP API] Sending JSON response: {data}")
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')  # Add CORS header
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        try:
            json_str = json.dumps(data)
            self.wfile.write(json_str.encode())
            print(f"[HTTP API] Successfully sent response")
        except Exception as e:
            print(f"[HTTP API] Error encoding JSON: {e}")
            self._send_error_response(500, f"JSON encoding error: {str(e)}")
    
    def _send_error_response(self, code, message):
        """Send error response"""
        print(f"[HTTP API] Sending error response: {code} - {message}")
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')  # Add CORS header
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        error_data = {"error": message, "code": code}
        try:
            self.wfile.write(json.dumps(error_data).encode())
        except Exception as e:
            print(f"[HTTP API] Error sending error response: {e}")

    def log_message(self, format, *args):
        """Override to reduce log spam"""
        return  # Comment this out if you want to see all HTTP logs

class HTTPAPIServer:
    def __init__(self, data_handler, host='0.0.0.0', port=8080):
        self.data_handler = data_handler
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
    
    def start(self):
        """Start HTTP API server in separate thread"""
        def run_server():
            try:
                handler = lambda *args, **kwargs: DataAPIHandler(self.data_handler, *args, **kwargs)
                self.server = HTTPServer((self.host, self.port), handler)
                print(f"[HTTP API] ✅ Server started on http://{self.host}:{self.port}")
                print(f"[HTTP API] Available endpoints:")
                print(f"  - GET /api/sensor - Current sensor data")
                print(f"  - GET /api/matrix - Current matrix data") 
                print(f"  - GET /api/sensor/history?hours=24 - Sensor history")
                print(f"  - GET /api/status - Server status")
                self.server.serve_forever()
            except Exception as e:
                print(f"[HTTP API] ❌ Server failed to start: {e}")
        
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