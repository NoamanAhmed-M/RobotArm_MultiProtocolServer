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
            "ESP32_Sensor": ["Web"],
            "RobotArm": ["Web"]
        }
    
    def route(self, message_obj, sender_name, sender_type="tcp"):
        """
        Route messages based on sender name using routing_table.
        """
        message_obj["sender"] = sender_name
        message_obj["sender_type"] = sender_type
        targets = self.routing_table.get(sender_name, [])
        
        print(f"[Router] Routing from '{sender_name}' ({sender_type}) → {targets}")
        print(f"[Router] Message: {message_obj}")

        if not targets:
            print(f"[Router] ❌ No routing targets for sender: {sender_name}")
            return
        
        for target in targets:
            if target == "Web":
                self.send_to_web(message_obj)
            else:
                self.send_to_tcp(target, message_obj)
    
    def send_to_web(self, message_obj):
        """Send message to all WebSocket clients"""
        try:
            if not self.server.loop:
                print("[Router] ❌ Event loop not available")
                return
                
            # Schedule the async coroutine to run in the event loop
            asyncio.run_coroutine_threadsafe(
                self._send_to_web_async(message_obj),
                self.server.loop
            )
        except Exception as e:
            print(f"[Router] ❌ Failed to forward to Web clients: {e}")
    
    async def _send_to_web_async(self, message_obj):
        """Actually send the message to WebSocket clients (async)"""
        if not hasattr(self.server, 'ws_clients'):
            print("[Router] ❌ WebSocket clients not initialized")
            return
            
        async with self.server.ws_lock:
            if not self.server.ws_clients:
                print("[Router] ⚠️ No WebSocket clients connected")
                return
                
            disconnected_clients = []
            success_count = 0
            
            for ws, name in list(self.server.ws_clients.items()):
                try:
                    if not ws.closed:
                        await ws.send(json.dumps(message_obj))
                        print(f"[Router] ✅ Sent to Web client: {name}")
                        success_count += 1
                    else:
                        disconnected_clients.append(ws)
                except Exception as e:
                    print(f"[Router] ❌ WebSocket send failed for {name}: {e}")
                    disconnected_clients.append(ws)
            
            # Clean up disconnected clients
            for ws in disconnected_clients:
                if ws in self.server.ws_clients:
                    name = self.server.ws_clients.pop(ws)
                    print(f"[Router] 🧹 Cleaned up disconnected client: {name}")
                try:
                    await ws.close()
                except:
                    pass
            
            print(f"[Router] ✅ Message sent to {success_count} WebSocket clients")
    
    def send_to_tcp(self, target_name, message_obj):
        """Send message to specific TCP client"""
        with self.server.tcp_lock:
            found = False
            disconnected_clients = []
            
            for sock, name in list(self.server.tcp_clients.items()):
                if name == target_name:
                    found = True
                    try:
                        message_str = json.dumps(message_obj) + '\n'  # Add newline for easier parsing
                        sock.send(message_str.encode('utf-8'))
                        print(f"[Router] ✅ Sent to TCP client: {name}")
                    except Exception as e:
                        print(f"[Router] ❌ TCP send failed for {name}: {e}")
                        disconnected_clients.append(sock)
            
            # Clean up disconnected clients
            for sock in disconnected_clients:
                if sock in self.server.tcp_clients:
                    name = self.server.tcp_clients.pop(sock)
                    print(f"[Router] 🧹 Cleaned up disconnected TCP client: {name}")
                try:
                    sock.close()
                except:
                    pass
            
            if not found:
                print(f"[Router] ❌ TCP client '{target_name}' not found")
    
    def add_routing_rule(self, sender, targets):
        """Dynamically add routing rule"""
        if isinstance(targets, str):
            targets = [targets]
        self.routing_table[sender] = targets
        print(f"[Router] ✅ Added routing rule: {sender} → {targets}")
    
    def remove_routing_rule(self, sender):
        """Remove routing rule"""
        if sender in self.routing_table:
            del self.routing_table[sender]
            print(f"[Router] ✅ Removed routing rule for: {sender}")
    
    def get_routing_table(self):
        """Get current routing table"""
        return self.routing_table.copy()
