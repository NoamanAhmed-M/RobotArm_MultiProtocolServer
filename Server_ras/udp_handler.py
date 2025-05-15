import socket
import asyncio
import json
import cv2
import numpy as np
import struct
import base64
import time
import traceback

class UDPHandler:
    def __init__(self, server):
        self.server = server
        self.MAX_DGRAM = 65507
    
    async def broadcast_frames(self):
        """Broadcast video frames to connected WebSocket clients"""
        last_log_time = time.time()
        while True:
            try:
                # Skip if no clients
                if not self.server.video_ws_clients:
                    await asyncio.sleep(0.1)
                    continue

                # Get frame from queue with timeout
                try:
                    frame_data = await asyncio.wait_for(self.server.frame_queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    await asyncio.sleep(0.1)
                    continue
                
                self.server.frame_count += 1
                
                # Format the frame data correctly for the frontend
                frame_message = json.dumps({
                    "type": "video_frame",
                    "data": frame_data,
                    "frame_num": self.server.frame_count,
                    "timestamp": time.time()
                })
                
                # Send frame to all connected video clients
                failed_clients = []
                success_count = 0
                
                for client in self.server.video_ws_clients:
                    try:
                        await client.send(frame_message)
                        success_count += 1
                        self.server.frames_sent += 1
                    except Exception as e:
                        print(f"[WS Video] Failed to send to client: {e}")
                        failed_clients.append(client)
                
                # Clean up failed clients
                for client in failed_clients:
                    if client in self.server.video_ws_clients:
                        self.server.video_ws_clients.discard(client)

                now = time.time()
                # Log broadcast stats periodically
                if now - last_log_time >= 5.0:
                    print(f"[Video] Frame {self.server.frame_count} sent to {success_count}/{len(self.server.video_ws_clients)} clients. Queue size: {self.server.frame_queue.qsize()}")
                    last_log_time = now
                    
            except Exception as e:
                print(f"[Broadcast Error] {e}")
                traceback.print_exc()
                await asyncio.sleep(0.1)

    async def udp_receiver(self):
        """Receive and process UDP video stream packets"""
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.server.udp_host, self.server.udp_port))
        sock.setblocking(False)
        
        last_log_time = time.time()

        while True:
            try:
                data, addr = await loop.sock_recvfrom(sock, self.MAX_DGRAM)
                if len(data) < 8:
                    continue

                frame_num, total_chunks = struct.unpack(">II", data[:8])
                chunk_data = data[8:]

                if frame_num not in self.server.buffer_dict:
                    self.server.buffer_dict[frame_num] = {'chunks': {}, 'total': total_chunks, 'timestamp': time.time()}
                self.server.buffer_dict[frame_num]['chunks'][len(chunk_data)] = chunk_data

                if len(self.server.buffer_dict[frame_num]['chunks']) == total_chunks:
                    now = time.time()
                    if now - last_log_time >= 5.0:
                        print(f"[UDP] Frame {frame_num} complete ({total_chunks} chunks)")
                        last_log_time = now
                    
                    try:
                        # Process complete frame
                        await self._process_complete_frame(frame_num)
                    except Exception as e:
                        print(f"[UDP] Frame processing error: {e}")
                        traceback.print_exc()
                    finally:
                        del self.server.buffer_dict[frame_num]

                # Clean up old incomplete frames
                self._clean_stale_frames()

            except Exception as e:
                if "Resource temporarily unavailable" not in str(e):
                    print(f"[UDP Error] {e}")
                await asyncio.sleep(0.01)
    
    async def _process_complete_frame(self, frame_num):
        """Process a complete frame once all chunks are received"""
        frame_info = self.server.buffer_dict[frame_num]
        full_data = b''.join(frame_info['chunks'][k] for k in sorted(frame_info['chunks'].keys()))
        img_np = np.frombuffer(full_data, dtype=np.uint8)
        frame = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
        
        if frame is not None:
            frame = cv2.resize(frame, (640, 480))
            # Add frame number as text overlay
            cv2.putText(frame, f"Frame: {frame_num}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            _, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            b64_data = base64.b64encode(jpeg.tobytes()).decode('utf-8')
            
            self.server.frames_processed += 1
            
            # Add to queue with timeout to avoid blocking
            try:
                if self.server.frame_queue.full():
                    # If queue is full, get an item first
                    try:
                        self.server.frame_queue.get_nowait()
                    except:
                        pass
                
                # Now put the new frame
                await asyncio.wait_for(self.server.frame_queue.put(b64_data), timeout=0.1)
                if self.server.frames_processed % 100 == 0:
                    print(f"[UDP] Frame {frame_num} queued for broadcast (processed {self.server.frames_processed} total)")
            except asyncio.QueueFull:
                print("[UDP] Frame queue full - dropping frame")
            except asyncio.TimeoutError:
                print("[UDP] Timeout adding frame to queue")
    
    def _clean_stale_frames(self):
        """Clean up stale incomplete frames from buffer"""
        now = time.time()
        stale_frames = []
        for f in self.server.buffer_dict:
            if now - self.server.buffer_dict[f]['timestamp'] > 5:
                stale_frames.append(f)
        
        for f in stale_frames:
            del self.server.buffer_dict[f]
