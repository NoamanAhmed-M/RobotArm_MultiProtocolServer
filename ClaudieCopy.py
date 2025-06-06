import asyncio
import threading
import time
from collections import defaultdict
from threading import Lock

# Import your existing modules
from tcp_handler import TCPHandler
from websocket_handler import WebSocketHandler
from udp_handler import UDPHandler
from data_handler import DataHandler
from http_api import HTTPAPIServer
from status_router import MessageRouter

class MultiProtocolServer:
    def __init__(self):
        # Network configuration
        self.tcp_host = '0.0.0.0'
        self.tcp_port = 9999
        self.ws_host = '0.0.0.0'
        self.ws_port = 8765  # Chat WebSocket
        self.video_ws_port = 8766  # Video WebSocket
        self.udp_host = '0.0.0.0'
        self.udp_port = 5000
        self.http_port = 8080
        
        # Client management
        self.tcp_clients = {}  # {socket: name}
        self.ws_clients = {}   # {websocket: name}
        self.video_ws_clients = set()  # Set of video websocket connections
        
        # Thread safety
        self.tcp_lock = Lock()
        self.ws_lock = asyncio.Lock()
        
        # Video streaming
        self.frame_queue = asyncio.Queue(maxsize=10)
        self.buffer_dict = {}
        self.frame_count = 0
        self.frames_processed = 0
        self.frames_sent = 0
        
        # Initialize components
        self.data_handler = DataHandler()
        self.router = MessageRouter(self)
        self.tcp_handler = TCPHandler(self)
        self.ws_handler = WebSocketHandler(self)
        self.udp_handler = UDPHandler(self)
        self.http_server = HTTPAPIServer(self.data_handler, port=self.http_port)
        
        # Event loop reference for threading
        self.loop = None
        
        print("[Server] ✅ MultiProtocolServer initialized")
    
    def start(self):
        """Start all server components"""
        print("[Server] 🚀 Starting MultiProtocolServer...")
        
        # Start HTTP API first
        self.http_server.start()
        
        # Start TCP server in separate thread
        tcp_thread = threading.Thread(target=self.tcp_handler.start_tcp_server, daemon=True)
        tcp_thread.start()
        print(f"[Server] ✅ TCP server started on {self.tcp_host}:{self.tcp_port}")
        
        # Start asyncio event loop for WebSocket and UDP
        try:
            asyncio.run(self._start_async_servers())
        except KeyboardInterrupt:
            print("\n[Server] 🛑 Shutting down...")
        except Exception as e:
            print(f"[Server] ❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
    
    async def _start_async_servers(self):
        """Start WebSocket and UDP servers in async context"""
        self.loop = asyncio.get_running_loop()
        
        # Create WebSocket servers
        chat_server = self.ws_handler.create_chat_server()
        video_server = self.ws_handler.create_video_server(self.video_ws_port)
        
        print(f"[Server] ✅ Chat WebSocket server starting on {self.ws_host}:{self.ws_port}")
        print(f"[Server] ✅ Video WebSocket server starting on {self.ws_host}:{self.video_ws_port}")
        
        # Start all async tasks
        await asyncio.gather(
            chat_server,
            video_server,
            self.udp_handler.udp_receiver(),
            self.udp_handler.broadcast_frames(),
            self._stats_reporter()
        )
    
    async def _stats_reporter(self):
        """Periodically report server statistics"""
        while True:
            await asyncio.sleep(30)  # Report every 30 seconds
            
            async with self.ws_lock:
                tcp_count = len(self.tcp_clients)
                ws_count = len(self.ws_clients)
                video_count = len(self.video_ws_clients)
            
            print(f"[Server Stats] TCP: {tcp_count}, WS: {ws_count}, Video: {video_count}")
            print(f"[Video Stats] Processed: {self.frames_processed}, Sent: {self.frames_sent}, Queue: {self.frame_queue.qsize()}")
    
    def get_client_info(self):
        """Get information about connected clients"""
        with self.tcp_lock:
            tcp_clients = list(self.tcp_clients.values())
        
        # Note: Can't use async lock here, so this is approximate
        ws_clients = list(self.ws_clients.values()) if hasattr(self, 'ws_clients') else []
        
        return {
            "tcp_clients": tcp_clients,
            "ws_clients": ws_clients,
            "video_clients": len(self.video_ws_clients),
            "total_frames_processed": self.frames_processed,
            "total_frames_sent": self.frames_sent
        }

if __name__ == "__main__":
    server = MultiProtocolServer()
    server.start()
