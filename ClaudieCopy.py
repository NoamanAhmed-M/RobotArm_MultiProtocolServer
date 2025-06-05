# Fixed http_api.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import time  # ✅ Added missing import
from urllib.parse import urlparse, parse_qs

class DataAPIHandler(BaseHTTPRequestHandler):
    def __init__(self, data_handler, *args, **kwargs):
        print("Created HTTP_API_data handler")
        self.data_handler = data_handler
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for data"""
        print("HTTP GET request")
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        # ✅ Move CORS headers to the beginning and make them consistent
        self.send_response(200)  # Default to 200, will be overridden if needed
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        
        try:
            if path == '/api/sensor':
                print("api/sensor PATH")
                data = self.data_handler.get_sensor_data()
                # ✅ Fixed: Convert dict to string properly for logging
                print("Collected sensor data from file: " + str(data))
                self._send_json_response(data)
            
            elif path == '/api/matrix':
                data = self.data_handler.get_matrix_data()
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
        # ✅ Fixed: Convert dict to string properly for logging
        print("Sending to client: " + str(data))
        if data is None:
            self._send_error_response(404, "Data not found")
            return
        
        # ✅ Headers already sent in do_GET, just send content-type and body
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _send_error_response(self, code, message):
        """Send error response"""
        # ✅ Override the default 200 response
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        error_data = {"error": message, "code": code}
        self.wfile.write(json.dumps(error_data).encode())

class HTTPAPIServer:
    def __init__(self, data_handler, host='0.0.0.0', port=8080):
        self.data_handler = data_handler
        self.host = host
        self.port = port
        self.server = None
    
    def start(self):
        """Start HTTP API server in separate thread"""
        def run_server():
            handler = lambda *args, **kwargs: DataAPIHandler(self.data_handler, *args, **kwargs)
            self.server = HTTPServer((self.host, self.port), handler)
            print(f"[HTTP API] Server started on http://{self.host}:{self.port}")
            print(f"[HTTP API] Available endpoints:")
            print(f"  - GET /api/sensor - Current sensor data")
            print(f"  - GET /api/matrix - Current matrix data") 
            print(f"  - GET /api/sensor/history?hours=24 - Sensor history")
            print(f"  - GET /api/status - Server status")
            self.server.serve_forever()
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
    
    def stop(self):
        """Stop HTTP API server"""
        if self.server:
            self.server.shutdown()
