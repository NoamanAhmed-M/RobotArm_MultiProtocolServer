import json
import asyncio

class MessageRouter:
    def __init__(self, server):
        self.server = server

        # ✅ Define routing rules by client name
        self.routing_table = {
            "ESP_Matrix": ["Web"],
            "Web": ["RobotArm"],
            "ESP_Boolean": ["Web", "RobotArm"],
            "ESP_Sensor": ["Web"]:, #added ESP32 routing
            "RobotArm": ["Web"]
        }

    def route(self, message_obj, sender_name, sender_type="tcp"):
        """
        Route messages based on sender name using routing_table.
        """
        message_obj["sender"] = sender_name
        targets = self.routing_table.get(sender_name, [])

        print(f"[Router] Routing from '{sender_name}' → {targets}")

        if not targets:
            print(f"[Router] ❌ No routing targets for sender: {sender_name}")
            return

        for target in targets:
            if target == "Web":
                self.send_to_web(message_obj)
            else:
                self.send_to_tcp(target, message_obj)

    def send_to_web(self, message_obj):
        try:
            loop = self.server.loop  # Must be set in server.py
            asyncio.run_coroutine_threadsafe(
                self._send_to_web(message_obj),
                loop
            )
        except Exception as e:
            print(f"[Router] ❌ Failed to forward to Web clients: {e}")

    async def _send_to_web(self, message_obj):
        with self.server.ws_lock:
            for ws, name in list(self.server.ws_clients.items()):
                try:
                    await ws.send(json.dumps(message_obj))
                    print(f"[Router] ✅ Sent to Web client: {name}")
                except Exception as e:
                    print(f"[Router] ❌ WebSocket send failed for {name}: {e}")
                    self.server.ws_clients.pop(ws, None)
                    try:
                        await ws.close()
                    except:
                        pass

    def send_to_tcp(self, target_name, message_obj):
        with self.server.tcp_lock:
            for sock, name in list(self.server.tcp_clients.items()):
                if name == target_name:
                    try:
                        sock.send(json.dumps(message_obj).encode('utf-8'))
                        print(f"[Router] ✅ Sent to TCP client: {name}")
                    except Exception as e:
                        print(f"[Router] ❌ TCP send failed for {name}: {e}")
                        self.server.tcp_clients.pop(sock, None)
                        try:
                            sock.close()
                        except:
                            pass
