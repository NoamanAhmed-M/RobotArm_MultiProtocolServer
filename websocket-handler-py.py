import websockets
import json
import time
import cv2
import numpy as np
import base64
import traceback

class WebSocketHandler:
    def __init__(self, server):
        self.server = server

    def create_chat_server(self):
        """Create WebSocket server for chat messages"""
        return websockets.serve(self.handle_websocket_client, 
                               self.server.ws_host, 
                               self.server.ws_port)
    
    def create_video_server(self, video_ws_port):
        """Create WebSocket server for video streaming"""
        return websockets.serve(self.handle_video_websocket_client, 
                               self.server.ws_host, 
                               video_ws_port)
                               
    async def handle_websocket_client(self, websocket):
        """Handle regular WebSocket chat clients"""
        name = await websocket.recv()
        with self.server.ws_lock:
            self.server.ws_clients[websocket] = name
        print(f"[WS] {name} connected")

        try:
            async for message in websocket:
                message_obj = json.loads(message)
                print(f"[WS] Message from {name}: {message_obj}")
                await self.route_ws_message(message_obj, name, websocket)
        except Exception as e:
            print(f"[WS Error] Client error: {e}")
        finally:
            with self.server.ws_lock:
                self.server.ws_clients.pop(websocket, None)
            print(f"[WS] {name} disconnected")

    async def handle_video_websocket_client(self, websocket):
        """Handle WebSocket video streaming clients"""
        try:
            client_ip = websocket.remote_address[0]
            print(f"[WS Video] Client connected from {client_ip}")
            self.server.video_ws_clients.add(websocket)
            
            # Send initial connection confirmation
            try:
                test_message = json.dumps({
                    "status": "connected", 
                    "message": "Video stream connected",
                    "timestamp": time.time()
                })
                await websocket.send(test_message)
                print(f"[WS Video] Sent connection confirmation to {client_ip}")
            except Exception as e:
                print(f"[WS Video] Failed to send test message: {e}")
            
            # Send a test image frame to verify connection
            try:
                # Create a simple test image
                test_img = np.ones((480, 640, 3), dtype=np.uint8) * 128  # Gray image
                # Add text
                cv2.putText(test_img, "Test Frame", (220, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                # Encode and send
                _, jpeg = cv2.imencode('.jpg', test_img)
                b64_data = base64.b64encode(jpeg.tobytes()).decode('utf-8')
                
                test_frame = json.dumps({
                    "type": "video_frame",
                    "data": b64_data,
                    "timestamp": time.time(),
                    "test": True
                })
                await websocket.send(test_frame)
                print(f"[WS Video] Sent test frame to {client_ip}")
            except Exception as e:
                print(f"[WS Video] Failed to send test frame: {e}")
                traceback.print_exc()
            
            # Wait until the connection is closed
            await websocket.wait_closed()
        except Exception as e:
            print(f"[WS Video] Error in client handler: {e}")
            traceback.print_exc()
        finally:
            if websocket in self.server.video_ws_clients:
                self.server.video_ws_clients.discard(websocket)
                print(f"[WS Video] Client from {websocket.remote_address[0] if hasattr(websocket, 'remote_address') else 'unknown'} disconnected")
    
    async def route_ws_message(self, message_obj, sender_name, sender_websocket):
        """Route messages from WebSocket clients to appropriate destinations"""
        targets = self.server.get_target_recipients(sender_name)
        with self.server.ws_lock:
            for ws, client_name in list(self.server.ws_clients.items()):
                if ws == sender_websocket:
                    continue
                if "*" in targets or client_name in targets:
                    try:
                        message_obj["sender"] = sender_name
                        await ws.send(json.dumps(message_obj))
                    except:
                        self.server.ws_clients.pop(ws, None)
