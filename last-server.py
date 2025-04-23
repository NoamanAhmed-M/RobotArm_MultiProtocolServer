import socket
import threading
import asyncio
import websockets
import json
import numpy as np
import cv2
import struct
import base64
import time
import traceback

class MultiProtocolServer:
    def __init__(self, tcp_host='0.0.0.0', tcp_port=5555, ws_host='0.0.0.0', ws_port=8765, udp_host='0.0.0.0', udp_port=5005):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.ws_host = ws_host
        self.ws_port = ws_port
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.MAX_DGRAM = 65507

        self.tcp_clients = {}
        self.ws_clients = {}
        self.video_ws_clients = set()

        self.frame_queue = asyncio.Queue(maxsize=10)
        self.buffer_dict = {}
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.frames_sent = 0
        self.frames_processed = 0

        self.routing_rules = {
            "client1": ["client2"],
            "client2": ["client1"],
            "admin": ["*"]
        }

        self.tcp_lock = threading.Lock()
        self.ws_lock = threading.Lock()

    def start(self):
        tcp_thread = threading.Thread(target=self.start_tcp_server, daemon=True)
        tcp_thread.start()
        asyncio.run(self.start_async_servers())

    def start_tcp_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.tcp_host, self.tcp_port))
            server_socket.listen()
            print(f"[TCP] Server started on {self.tcp_host}:{self.tcp_port}")

            while True:
                client_socket, client_address = server_socket.accept()
                threading.Thread(target=self.handle_tcp_client, args=(client_socket, client_address), daemon=True).start()

    def handle_tcp_client(self, client_socket, client_address):
        name = None
        try:
            name = client_socket.recv(1024).decode('utf-8').strip()
            if not name:
                return

            with self.tcp_lock:
                self.tcp_clients[client_socket] = name
            print(f"[TCP] {name} connected from {client_address}")

            while True:
                data = client_socket.recv(4096)
                if not data:
                    break

                message_obj = json.loads(data.decode('utf-8'))
                print(f"[TCP] Message from {name}: {message_obj}")
                self.route_tcp_message(message_obj, name, client_socket)

        except Exception as e:
            print(f"[TCP Error] {e}")
        finally:
            with self.tcp_lock:
                self.tcp_clients.pop(client_socket, None)
            client_socket.close()
            print(f"[TCP] {name or client_address} disconnected")

    async def start_async_servers(self):
        print("[Async] Starting WebSocket and UDP servers...")
        
        # Configure WebSocket servers
        video_ws_port = self.ws_port + 1
        
        # Start UDP receiver separately
        udp_task = asyncio.create_task(self.udp_receiver())
        broadcast_task = asyncio.create_task(self.broadcast_frames())
        stats_task = asyncio.create_task(self.display_fps())
        
        print(f"[WS] Chat Server starting on {self.ws_host}:{self.ws_port}")
        print(f"[WS] Video Server starting on {self.ws_host}:{video_ws_port}")
        print(f"[UDP] Listening on {self.udp_host}:{self.udp_port}")
        
        # Start both WebSocket servers
        async with websockets.serve(self.handle_websocket_client, self.ws_host, self.ws_port) as chat_server:
            print(f"[WS] Chat Server running on {self.ws_host}:{self.ws_port}")
            async with websockets.serve(self.handle_video_websocket_client, self.ws_host, video_ws_port) as video_server:
                print(f"[WS] Video Server running on {self.ws_host}:{video_ws_port}")
                await asyncio.gather(udp_task, broadcast_task, stats_task)

    async def handle_websocket_client(self, websocket):
        name = await websocket.recv()
        with self.ws_lock:
            self.ws_clients[websocket] = name
        print(f"[WS] {name} connected")

        try:
            async for message in websocket:
                message_obj = json.loads(message)
                print(f"[WS] Message from {name}: {message_obj}")
                await self.route_ws_message(message_obj, name, websocket)
        except Exception as e:
            print(f"[WS Error] Client error: {e}")
        finally:
            with self.ws_lock:
                self.ws_clients.pop(websocket, None)
            print(f"[WS] {name} disconnected")

    async def handle_video_websocket_client(self, websocket):
        try:
            client_ip = websocket.remote_address[0]
            print(f"[WS Video] Client connected from {client_ip}")
            self.video_ws_clients.add(websocket)
            
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
            if websocket in self.video_ws_clients:
                self.video_ws_clients.discard(websocket)
                print(f"[WS Video] Client from {websocket.remote_address[0] if hasattr(websocket, 'remote_address') else 'unknown'} disconnected")

    async def broadcast_frames(self):
        last_log_time = time.time()
        while True:
            try:
                # Skip if no clients
                if not self.video_ws_clients:
                    await asyncio.sleep(0.1)
                    continue

                # Get frame from queue with timeout
                try:
                    frame_data = await asyncio.wait_for(self.frame_queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    await asyncio.sleep(0.1)
                    continue
                
                self.frame_count += 1
                
                # Format the frame data correctly for the frontend
                frame_message = json.dumps({
                    "type": "video_frame",
                    "data": frame_data,
                    "frame_num": self.frame_count,
                    "timestamp": time.time()
                })
                
                # Send frame to all connected video clients
                failed_clients = []
                success_count = 0
                
                for client in self.video_ws_clients:
                    try:
                        await client.send(frame_message)
                        success_count += 1
                        self.frames_sent += 1
                    except Exception as e:
                        print(f"[WS Video] Failed to send to client: {e}")
                        failed_clients.append(client)
                
                # Clean up failed clients
                for client in failed_clients:
                    if client in self.video_ws_clients:
                        self.video_ws_clients.discard(client)

                now = time.time()
                # Log broadcast stats periodically
                if now - last_log_time >= 5.0:
                    print(f"[Video] Frame {self.frame_count} sent to {success_count}/{len(self.video_ws_clients)} clients. Queue size: {self.frame_queue.qsize()}")
                    last_log_time = now
                    
            except Exception as e:
                print(f"[Broadcast Error] {e}")
                traceback.print_exc()
                await asyncio.sleep(0.1)

    async def udp_receiver(self):
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.udp_host, self.udp_port))
        sock.setblocking(False)
        
        last_log_time = time.time()

        while True:
            try:
                data, addr = await loop.sock_recvfrom(sock, self.MAX_DGRAM)
                if len(data) < 8:
                    continue

                frame_num, total_chunks = struct.unpack(">II", data[:8])
                chunk_data = data[8:]

                if frame_num not in self.buffer_dict:
                    self.buffer_dict[frame_num] = {'chunks': {}, 'total': total_chunks, 'timestamp': time.time()}
                self.buffer_dict[frame_num]['chunks'][len(chunk_data)] = chunk_data

                if len(self.buffer_dict[frame_num]['chunks']) == total_chunks:
                    now = time.time()
                    if now - last_log_time >= 5.0:
                        print(f"[UDP] Frame {frame_num} complete ({total_chunks} chunks)")
                        last_log_time = now
                    
                    try:
                        full_data = b''.join(self.buffer_dict[frame_num]['chunks'][k] for k in sorted(self.buffer_dict[frame_num]['chunks'].keys()))
                        img_np = np.frombuffer(full_data, dtype=np.uint8)
                        frame = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            frame = cv2.resize(frame, (640, 480))
                            # Add frame number as text overlay
                            cv2.putText(frame, f"Frame: {frame_num}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            
                            _, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                            b64_data = base64.b64encode(jpeg.tobytes()).decode('utf-8')
                            
                            self.frames_processed += 1
                            
                            # Add to queue with timeout to avoid blocking
                            try:
                                if self.frame_queue.full():
                                    # If queue is full, get an item first
                                    try:
                                        self.frame_queue.get_nowait()
                                    except:
                                        pass
                                
                                # Now put the new frame
                                await asyncio.wait_for(self.frame_queue.put(b64_data), timeout=0.1)
                                if self.frames_processed % 100 == 0:
                                    print(f"[UDP] Frame {frame_num} queued for broadcast (processed {self.frames_processed} total)")
                            except asyncio.QueueFull:
                                print("[UDP] Frame queue full - dropping frame")
                            except asyncio.TimeoutError:
                                print("[UDP] Timeout adding frame to queue")
                    except Exception as e:
                        print(f"[UDP] Frame processing error: {e}")
                        traceback.print_exc()
                    finally:
                        del self.buffer_dict[frame_num]

                # Clean up old frames
                now = time.time()
                stale_frames = []
                for f in self.buffer_dict:
                    if now - self.buffer_dict[f]['timestamp'] > 5:
                        stale_frames.append(f)
                
                for f in stale_frames:
                    del self.buffer_dict[f]

            except Exception as e:
                if "Resource temporarily unavailable" not in str(e):
                    print(f"[UDP Error] {e}")
                await asyncio.sleep(0.01)

    async def display_fps(self):
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
        targets = self.routing_rules.get(sender_name, [])
        return targets if "*" not in targets else ["*"]

    def route_tcp_message(self, message_obj, sender_name, sender_socket):
        targets = self.get_target_recipients(sender_name)
        with self.tcp_lock:
            for client_socket, client_name in list(self.tcp_clients.items()):
                if client_socket == sender_socket:
                    continue
                if "*" in targets or client_name in targets:
                    try:
                        message_obj["sender"] = sender_name
                        client_socket.send(json.dumps(message_obj).encode("utf-8"))
                    except:
                        self.tcp_clients.pop(client_socket, None)

    async def route_ws_message(self, message_obj, sender_name, sender_websocket):
        targets = self.get_target_recipients(sender_name)
        with self.ws_lock:
            for ws, client_name in list(self.ws_clients.items()):
                if ws == sender_websocket:
                    continue
                if "*" in targets or client_name in targets:
                    try:
                        message_obj["sender"] = sender_name
                        await ws.send(json.dumps(message_obj))
                    except:
                        self.ws_clients.pop(ws, None)

def main():
    server = MultiProtocolServer()
    server.start()

if __name__ == "__main__":
    main()
