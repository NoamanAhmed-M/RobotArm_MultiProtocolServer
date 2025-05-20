import websockets
import json
import time
import traceback

class WebSocketHandler:
    def __init__(self, server):
        self.server = server

    def create_chat_server(self):
        return websockets.serve(
            self.handle_websocket_client,
            self.server.ws_host,
            self.server.ws_port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5
        )

    def create_video_server(self, video_ws_port):
        return websockets.serve(
            self.handle_video_websocket_client,
            self.server.ws_host,
            video_ws_port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5
        )

    async def handle_websocket_client(self, websocket):
        """Handles chat/control clients (e.g., Web, RobotArm)"""
        try:
            # Receive initial client name
            base_name = await websocket.recv()
            if not base_name:
                await websocket.close()
                return

            # Generate unique name if necessary
            counter = 1
            name = base_name
            existing_names = set(self.server.ws_clients.values())
            while name in existing_names:
                name = f"{base_name}_{counter}"
                counter += 1

            self.server.ws_clients[websocket] = name
            print(f"[WS] {name} connected")

            # Send connection confirmation with assigned name
            await websocket.send(json.dumps({
                "type": "status",
                "msg": f"{name} connected successfully",
                "name": name,
                "timestamp": time.time()
            }))

            # Handle incoming messages
            async for message in websocket:
                try:
                    message_obj = json.loads(message)
                    self.server.router.route(message_obj, sender_name=name, sender_type="websocket")
                except Exception as e:
                    print(f"[WS Error] Failed to process message from {name}: {e}")
                    traceback.print_exc()

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"[WS Handler Error] {e}")
            traceback.print_exc()
        finally:
            # Cleanup on disconnect
            disconnected_name = self.server.ws_clients.get(websocket, "Unknown")
            print(f"[WS] {disconnected_name} disconnected")
            self.server.ws_clients.pop(websocket, None)

    async def handle_video_websocket_client(self, websocket):
        """Handles video stream clients"""
        try:
            self.server.video_ws_clients.add(websocket)
            print(f"[Video WS] New video client connected")

            async for _ in websocket:
                pass  # Ignore messages from video clients (if any)

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"[Video WS Error] {e}")
            traceback.print_exc()
        finally:
            self.server.video_ws_clients.discard(websocket)
            print(f"[Video WS] Client disconnected")
