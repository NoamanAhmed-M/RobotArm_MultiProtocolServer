import socket
import threading
import cv2
import numpy as np
import struct
import asyncio
import websockets
import base64
import json

class IntegratedServer:
    def __init__(self, tcp_host='0.0.0.0', tcp_port=5555, ws_host='0.0.0.0', ws_port=8765, udp_host='0.0.0.0', udp_port=5005):
        # Data transmission server parameters
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.ws_host = ws_host
        self.ws_port = ws_port
        
        # Video streaming parameters
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.MAX_DGRAM = 65507
        
        # Client tracking
        self.tcp_clients = {}  # {socket: name}
        self.ws_clients = {}   # {websocket: name}
        self.device_routing = {}  # {sender_name: [target_names]}
        
        # Video streaming
        self.buffer_dict = {}
        self.frame_queue = asyncio.Queue()
        
        # Locks
        self.tcp_lock = threading.Lock()
        self.ws_lock = threading.Lock()

    def start(self):
        # Start TCP server in a separate thread
        tcp_thread = threading.Thread(target=self.start_tcp_server, daemon=True)
        tcp_thread.start()

        # Start WebSocket server and UDP receiver using asyncio
        asyncio.run(self.start_services())
    
    async def start_services(self):
        # Start both WebSocket server and UDP receiver
        ws_server = await websockets.serve(self.handle_websocket_client, self.ws_host, self.ws_port)
        print(f"WebSocket Server started on {self.ws_host}:{self.ws_port}")
        
        # Start UDP receiver
        udp_task = asyncio.create_task(self.udp_receiver())
        
        # Start frame broadcaster
        broadcast_task = asyncio.create_task(self.broadcast_frames())
        
        print("All services started")
        await asyncio.Future()  # run forever

    def start_tcp_server(self):
        """Start TCP server"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.tcp_host, self.tcp_port))
            server_socket.listen()
            print(f"TCP Server started on {self.tcp_host}:{self.tcp_port}")

            while True:
                try:
                    client_socket, client_address = server_socket.accept()
                    threading.Thread(
                        target=self.handle_tcp_client,
                        args=(client_socket, client_address),
                        daemon=True
                    ).start()
                except Exception as e:
                    print(f"TCP server error: {e}")

    def handle_tcp_client(self, client_socket, client_address):
        """Handle TCP client"""
        name = None
        try:
            name = client_socket.recv(1024).decode('utf-8').strip()
            if not name:
                client_socket.close()
                return

            with self.tcp_lock:
                self.tcp_clients[client_socket] = name

            print(f"New TCP client: {name} ({client_address})")

            while True:
                message = client_socket.recv(1024).decode('utf-8').strip()
                if not message:
                    break
                print(f"TCP Message from {name}: {message}")
                self.route_tcp_message(message, sender_name=name, sender_socket=client_socket)

        except Exception as e:
            print(f"TCP client error with {client_address}: {e}")
        finally:
            with self.tcp_lock:
                self.tcp_clients.pop(client_socket, None)
            client_socket.close()
            print(f"TCP client {name or client_address} disconnected.")

    async def handle_websocket_client(self, websocket, path):
        """Handle WebSocket client"""
        name = None
        try:
            # First message should be client name
            name = await websocket.recv()
            with self.ws_lock:
                self.ws_clients[websocket] = name

            print(f"New WebSocket client: {name}")
            
            # Send a welcome message with information about available streams
            await websocket.send(json.dumps({
                "type": "welcome",
                "message": f"Welcome {name}! You can subscribe to video streams."
            }))

            async for message in websocket:
                try:
                    # Check if the message is a JSON command
                    data = json.loads(message)
                    if data.get("type") == "subscribe" and data.get("stream") == "video":
                        print(f"Client {name} subscribed to video stream")
                        # Subscribe this client to video frames
                        # Already implemented through the broadcast_frames method
                    else:
                        print(f"WebSocket Message from {name}: {message}")
                        await self.route_ws_message(message, sender_name=name, sender_websocket=websocket)
                except json.JSONDecodeError:
                    # Treat as regular message if not JSON
                    print(f"WebSocket Message from {name}: {message}")
                    await self.route_ws_message(message, sender_name=name, sender_websocket=websocket)

        except websockets.exceptions.ConnectionClosed:
            print(f"WebSocket client {name} disconnected")
        except Exception as e:
            print(f"WebSocket client error: {e}")
        finally:
            with self.ws_lock:
                self.ws_clients.pop(websocket, None)

    def route_tcp_message(self, message, sender_name, sender_socket):
        """Route TCP message to specific clients based on sender's routing rules"""
        target_recipients = self.device_routing.get(sender_name, [])
        
        with self.tcp_lock:
            for client_socket, client_name in list(self.tcp_clients.items()):
                if client_name in target_recipients and client_socket != sender_socket:
                    try:
                        client_socket.send(f"{sender_name}: {message}".encode('utf-8'))
                    except:
                        self.tcp_clients.pop(client_socket, None)

    async def route_ws_message(self, message, sender_name, sender_websocket):
        """Route WebSocket message to specific clients based on sender's routing rules"""
        target_recipients = self.device_routing.get(sender_name, [])
        
        with self.ws_lock:
            for ws, client_name in list(self.ws_clients.items()):
                if client_name in target_recipients and ws != sender_websocket:
                    try:
                        await ws.send(json.dumps({
                            "type": "chat",
                            "sender": sender_name,
                            "message": message
                        }))
                    except:
                        self.ws_clients.pop(ws, None)

    # Video streaming methods
    async def udp_receiver(self):
        """Receive UDP video frames and push to queue"""
        print(f"[UDP] Listening on {self.udp_host}:{self.udp_port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.udp_host, self.udp_port))
        sock.setblocking(False)
        
        while True:
            try:
                # Non-blocking recv with asyncio
                data, addr = await asyncio.get_event_loop().sock_recvfrom(sock, self.MAX_DGRAM)
                
                if len(data) < 4:
                    continue
                    
                # Extract frame metadata
                index, total = struct.unpack("HH", data[:4])
                chunk = data[4:]
                
                if index == 0:
                    self.buffer_dict.clear()
                
                self.buffer_dict[index] = chunk
                
                # Check if we have all chunks for a complete frame
                if len(self.buffer_dict) == total:
                    # Reconstruct the full frame
                    full_data = b''.join(self.buffer_dict[i] for i in range(total))
                    img_np = np.frombuffer(full_data, dtype=np.uint8)
                    frame = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # Encode the frame to JPG and base64
                        _, jpeg = cv2.imencode('.jpg', frame)
                        b64_data = base64.b64encode(jpeg.tobytes()).decode('utf-8')
                        
                        # Create a JSON message with the frame data
                        frame_msg = json.dumps({
                            "type": "video_frame",
                            "data": b64_data
                        })
                        
                        # Add to the queue for broadcasting
                        await self.frame_queue.put(frame_msg)
            except BlockingIOError:
                # No data available, wait a bit before trying again
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"UDP error: {e}")
                await asyncio.sleep(0.1)

    async def broadcast_frames(self):
        """Broadcast video frames to all connected WebSocket clients"""
        while True:
            # Get the next frame from the queue
            frame_msg = await self.frame_queue.get()
            
            # Send the frame to all connected WebSocket clients
            with self.ws_lock:
                for ws in list(self.ws_clients.keys()):
                    try:
                        await ws.send(frame_msg)
                    except:
                        # Client disconnected
                        pass

    # Set routing rules for devices (target devices for each sender)
    def set_device_routing(self, sender_name, target_names):
        """Define which devices a sender can communicate with"""
        self.device_routing[sender_name] = target_names

def main():
    server = IntegratedServer()
    # Example of setting routing rules
    server.set_device_routing("ESP32", ["ESP64", "WebClient"])  
    server.set_device_routing("ESP64", ["ESP32", "WebClient"])
    server.set_device_routing("WebClient", ["ESP32", "ESP64"])
    server.start()

if __name__ == "__main__":
    main()
