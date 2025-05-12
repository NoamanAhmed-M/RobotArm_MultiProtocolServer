class MessageRouter:
    def __init__(self, server):
        self.server = server

        # Define routing rules: who sends to whom
        self.routing_table = {
            "ESP_Matrix": ["Web"],
            "WebClient": ["RobotArm"],
            "ESP_Boolean": ["web", "RobotArm"],
            "RobotArm": ["web"]
        }

    def route(self, message_obj, sender_name, sender_type="tcp"):
        """
        Route message based on sender name using routing_table.
        """
        message_obj["sender"] = sender_name

        targets = self.routing_table.get(sender_name, [])
        if not targets:
            return

        for target in targets:
            if target == "web":
                self.send_to_web(message_obj)
            else:
                self.send_to_tcp(target, message_obj)

    def send_to_web(self, message_obj):
        asyncio.run_coroutine_threadsafe(
            self._send_to_web(message_obj),
            asyncio.get_event_loop()
        )

    async def _send_to_web(self, message_obj):
        with self.server.ws_lock:
            for ws in list(self.server.ws_clients):
                try:
                    await ws.send(json.dumps(message_obj))
                except:
                    self.server.ws_clients.pop(ws, None)

    def send_to_tcp(self, target_name, message_obj):
        with self.server.tcp_lock:
            for sock, name in self.server.tcp_clients.items():
                if name == target_name:
                    try:
                        sock.send(json.dumps(message_obj).encode('utf-8'))
                    except:
                        self.server.tcp_clients.pop(sock, None)
