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
            # Receive base name from client
            base_name = await websocket.recv()
            if not base_name:
                await websocket.close()
                return

            # Assign unique name if base name already used
            counter = 1
            name = base_name
            with self.server.ws_lock:
                existing_names = set(self.server.ws_clients.values())
                while name in existing_names:
                    name = f"{base_name}_{counter}"
                    counter += 1
                self.server.ws_clients[websocket] = name

            print(f"[WS] {name} connected")

            # Confirm connection
            await websocket.send(json.dumps({
                "type": "status",
                "msg": f"{name} connected successfully",
                "name": name,
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

                    # Echo back to sender
                    await websocket.send(json.dumps({
                        "type": "status",
                        "msg": f"Command received: {message_obj}",
                        "timestamp": time.time()
                    }))

                    # Broadcast to other WebSocket clients
                    with self.server.ws_lock:
                        for client_ws, client_name in self.server.ws_clients.items():
                            if client_ws != websocket:
                                await client_ws.send(json.dumps({
                                    "type": "status",
                                    "msg": f"{name} sent command: {message_obj}"
                                }))

                    # Route the command to the message router
                    self.server.router.route(message_obj, name, sender_type="ws")

                except Exception as e:
                    print(f"[WS ERROR] Failed to handle message from {name}: {e}")
                    traceback.print_exc()

        except Exception as e:
            print(f"[WS ERROR] Connection error: {e}")
            traceback.print_exc()

        finally:
            with self.server.ws_lock:
                if websocket in self.server.ws_clients:
                    print(f"[WS] {self.server.ws_clients[websocket]} disconnected")
                    del self.server.ws_clients[websocket]

    async def handle_video_websocket_client(self, websocket):
        """Handles video streaming clients"""
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
