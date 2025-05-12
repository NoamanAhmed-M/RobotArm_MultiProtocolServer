import threading
import asyncio
import time
from tcp_handler import TCPHandler
from websocket_handler import WebSocketHandler
from udp_handler import UDPHandler
from status_router import MessageRouter

class MultiProtocolServer:
    def __init__(self, tcp_host='0.0.0.0', tcp_port=5555, 
                 ws_host='0.0.0.0', ws_port=8765, 
                 udp_host='0.0.0.0', udp_port=5005):
        
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.ws_host = ws_host
        self.ws_port = ws_port
        self.udp_host = udp_host
        self.udp_port = udp_port
        
        # Shared state
        self.tcp_clients = {}
        self.ws_clients = {}
        self.video_ws_clients = set()
        self.frame_queue = asyncio.Queue(maxsize=10)
        self.buffer_dict = {}
        
        # Stats tracking
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.frames_sent = 0
        self.frames_processed = 0
        
        # Routing configuration
        self.routing_rules = {
            "client1": ["client2"],
            "client2": ["client1"],
            "admin": ["*"]
        }
        
        # Thread safety
        self.tcp_lock = threading.Lock()
        self.ws_lock = threading.Lock()
        
        # Initialize handlers
        self.tcp_handler = TCPHandler(self)
        self.ws_handler = WebSocketHandler(self)
        self.udp_handler = UDPHandler(self)

    def start(self):
        """Start all server components"""
        # Start TCP server in a separate thread
        tcp_thread = threading.Thread(target=self.tcp_handler.start_tcp_server, daemon=True)
        tcp_thread.start()
        
        # Run async components in the main thread
        asyncio.run(self.start_async_servers())
    
    async def start_async_servers(self):
        """Start all async server components (WebSocket and UDP)"""
        print("[Async] Starting WebSocket and UDP servers...")
        
        # Start UDP receiver task
        udp_task = asyncio.create_task(self.udp_handler.udp_receiver())
        broadcast_task = asyncio.create_task(self.udp_handler.broadcast_frames())
        stats_task = asyncio.create_task(self.display_stats())
        
        # Configure WebSocket servers
        video_ws_port = self.ws_port + 1
        print(f"[WS] Chat Server starting on {self.ws_host}:{self.ws_port}")
        print(f"[WS] Video Server starting on {self.ws_host}:{video_ws_port}")
        print(f"[UDP] Listening on {self.udp_host}:{self.udp_port}")
        
        # Start both WebSocket servers
        async with self.ws_handler.create_chat_server() as chat_server:
            print(f"[WS] Chat Server running on {self.ws_host}:{self.ws_port}")
            async with self.ws_handler.create_video_server(video_ws_port) as video_server:
                print(f"[WS] Video Server running on {self.ws_host}:{video_ws_port}")
                await asyncio.gather(udp_task, broadcast_task, stats_task)
    
    async def display_stats(self):
        """Display server statistics periodically"""
        while True:
            await asyncio.sleep(5)
            now = time.time()
            elapsed = now - self.last_frame_time
            fps = self.frame_count / elapsed if elapsed > 0 else 0
            
            queue_size = self.frame_queue.qsize() 
            print(f"[Stats] FPS: {fps:.2f}, Queue: {queue_size}, Clients: {len(self.video_ws_clients)}, " +
                  f"Processed: {self.frames_processed}, Sent: {self.frames_sent}")
            
            self.last_frame_time = now
            self.frame_count = 0
    
    def get_target_recipients(self, sender_name):
        """Determine which clients should receive a message based on routing rules"""
        targets = self.routing_rules.get(sender_name, [])
        return targets if "*" not in targets else ["*"]
