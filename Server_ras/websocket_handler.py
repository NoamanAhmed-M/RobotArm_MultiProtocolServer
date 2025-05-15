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
        return websockets.serve(
            self.handle_websocket_client,
            self.server.ws_host,
            self.server.ws_port
        )

    def create_video_server(self, video_ws_port):
        return websockets.serve(
            self.handle_video_websocket_client,
            self.server.ws_host,
            video_ws_port
        )

    async def handle_websocket_client(self, websocket):
        """Handles chat/control clients (e.g., Web, RobotArm)"""
        try:
            # First message: client name
            name = await websocket.recv()
            if not name:
                await websocket.close()
                return

            with self.server.ws_lock:
                self.server.ws_clients[websocket] = name
            print(f"[WS] {name} connected")

            # Confirm connection
            await websocket.send(json.dumps({
                "type": "status",
                "msg": f"{name} connected successfully",
                "timestamp": time.time()
            }))

            # Main receive loop
            async for message in websocket:
                print(f"[WS DEBUG] Raw message from {name}: {message}")
                try:
                    message_obj = json.loads(message)

                    # TEMP: Print ON/OFF commands
                    if message_obj.get("type") == "command":
                        if message_obj.get("value") is True:
                            print(f"[WS] ✅ ON command received from {name}")
                        elif message_obj.get("value") is False:
                            print(f"[WS] ❌ OFF command received from {name}")

                    # Optional: echo back
                    await websocket.send(json.dumps({
                        "type": "status",
                        "msg": f"Command received: {message_obj}",
                        "timestamp": time.time()
                    }))

                    # Optional: broadcast to others
                    with self.server.ws_lock:
                        for client_ws, client_name in self.server.ws_clients.items():
                            if client_ws != websocket:
                                await client_ws.send(json.dumps({
                                    "type": "status",
                                    "msg": f"{name} sent command: {message_obj}"
                                }))

                    # Route command to robot or internal logic
                    self.server.router.route(message_obj, name, sender_type="ws")

                except Exception as e:
                    print(f"[WS ERROR] Failed to handle message from {name}: {e}")
                    traceback.print_exc()

        except Exception as e:
            print(f"[WS ERROR] Connection error: {e}")
            traceback.print_exc()

        finally:
            with self.server.ws_lock:
                self.server.ws_clients.pop(websocket, None)
            print(f"[WS] {name if 'name' in locals() else 'Unknown'} disconnected")

    async def handle_video_websocket_client(self, websocket):
        """Sends test video frame to video canvas clients"""
        try:
            client_ip = websocket.remote_address[0]
            print(f"[WS Video] Client connected from {client_ip}")
            self.server.video_ws_clients.add(websocket)

            # Send confirmation
            await websocket.send(json.dumps({
                "status": "connected",
                "message": "Video stream connected",
                "timestamp": time.time()
            }))

            # Send test frame
            test_img = np.ones((480, 640, 3), dtype=np.uint8) * 128
            cv2.putText(test_img, "Test Frame", (220, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            _, jpeg = cv2.imencode('.jpg', test_img)
            b64_data = base64.b64encode(jpeg.tobytes()).decode('utf-8')

            await websocket.send(json.dumps({
                "type": "video_frame",
                "data": b64_data,
                "timestamp": time.time(),
                "test": True
            }))

            await websocket.wait_closed()

        except Exception as e:
            print(f"[WS Video] Error in client handler: {e}")
            traceback.print_exc()

        finally:
            self.server.video_ws_clients.discard(websocket)
            print(f"[WS Video] Client from {client_ip} disconnected")
