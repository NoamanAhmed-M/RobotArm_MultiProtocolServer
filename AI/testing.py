import sys
import cv2
import numpy as np
import pyrealsense2 as rs
import socket
import struct
import time
import json
import threading
import ast
from yoloDet import YoloTRT
from motor_control import move_forward_step, turn_left_step, turn_right_step, stop_all, cleanup

# === UDP Streaming Setup ===
UDP_IP = '192.168.43.114'
UDP_PORT = 5005
MAX_DGRAM = 65000
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# === TCP Control Setup ===
TCP_IP = '192.168.43.114'
TCP_PORT = 5555
CLIENT_NAME = "RobotArm"
RECONNECT_DELAY = 5
should_move = threading.Event()

# === YOLO Model Setup ===
model = YoloTRT(
    library="yolov5/buildMM/libmyplugins.so",
    engine="yolov5/buildMM/bestt.engine",
    conf=0.5,
    yolo_ver="v5"
)

# === RealSense Setup ===
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 424, 240, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 30)
profile = pipeline.start(config)

# Align depth with color frame
align = rs.align(rs.stream.color)

# === Helper: Get average depth around point (cx, cy) ===
def get_average_depth(depth_frame, cx, cy, k=5):
    values = [depth_frame.get_distance(cx + dx, cy + dy)
              for dx in range(-k//2, k//2 + 1)
              for dy in range(-k//2, k//2 + 1)
              if 0 <= cx + dx < depth_frame.get_width() and 0 <= cy + dy < depth_frame.get_height()]
    values = [v for v in values if 0 < v < 5]
    return np.mean(values) if values else 0

# === TCP Receive Thread Only ===
def start_tcp_receiver():
    def receive_commands(sock):
        while True:
            try:
                data = sock.recv(4096)
                if not data:
                    print("[RobotArm] ❌ Server closed connection")
                    break

                message = json.loads(data.decode('utf-8'))
                print(f"[SERVER -> RobotArm] {message}")

                if message.get("type") == "command":
                    should_move.set() if message.get("value") else should_move.clear()
                    print(f"[RobotArm] {'✅ Movement ENABLED' if should_move.is_set() else '⛔ Movement DISABLED'}")

                elif message.get("type") == "status" and "Command received" in message.get("msg", ""):
                    try:
                        embedded = ast.literal_eval(message["msg"].split("Command received: ")[1])
                        if embedded.get("type") == "command":
                            should_move.set() if embedded.get("value") else should_move.clear()
                            print(f"[RobotArm] {'✅ Movement ENABLED (embedded)' if should_move.is_set() else '⛔ Movement DISABLED (embedded)'}")
                    except Exception as e:
                        print(f"[RobotArm] ⚠️ Failed to parse embedded command: {e}")
            except Exception as e:
                print(f"[RobotArm] ❌ Receiving failed: {e}")
                break

    while True:
        try:
            print(f"[RobotArm] 🔌 Connecting to {TCP_IP}:{TCP_PORT}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((TCP_IP, TCP_PORT))
            print("[RobotArm] ✅ Connected to server")
            sock.send((CLIENT_NAME + "\n").encode('utf-8'))
            receive_commands(sock)
        except Exception as e:
            print(f"[RobotArm] ❌ Connection failed: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
            print(f"[RobotArm] 🔁 Reconnecting in {RECONNECT_DELAY} seconds...")
            time.sleep(RECONNECT_DELAY)

# Start TCP listener in background
threading.Thread(target=start_tcp_receiver, daemon=True).start()

# === Main Loop ===
frame_num = 0
last_fps_time = time.time()
frames_sent = 0

try:
    while True:
        frames = pipeline.wait_for_frames()
        aligned_frames = align.process(frames)
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        frame = np.asanyarray(color_frame.get_data())
        detections, t = model.Inference(frame)

        h, w, _ = frame.shape
        center_x = w // 2

        for det in detections:
            x1, y1, x2, y2 = map(int, det['box'])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            distance = get_average_depth(depth_frame, cx, cy)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{det['class']} {det['conf']:.2f}"
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(frame, f"{distance:.2f} m", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            offset = cx - center_x
            threshold = w // 10

            if should_move.is_set() and 0.4 < distance < 2.0:
                if offset < -threshold:
                    turn_left_step(20, 50, 0.1)
                elif offset > threshold:
                    turn_right_step(20, 50, 0.1)
                else:
                    move_forward_step(20, 50, 0.1)
            else:
                stop_all()
            break

        resized = cv2.resize(frame, (640, 480))
        _, encoded_img = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        img_data = encoded_img.tobytes()
        chunks = [img_data[i:i + MAX_DGRAM - 8] for i in range(0, len(img_data), MAX_DGRAM - 8)]
        for chunk in chunks:
            header = struct.pack('>II', frame_num, len(chunks))
            udp_sock.sendto(header + chunk, (UDP_IP, UDP_PORT))

        frame_num += 1
        frames_sent += 1

        now = time.time()
        if now - last_fps_time >= 5:
            fps = frames_sent / (now - last_fps_time)
            print(f"[UDP] FPS: {fps:.2f}")
            frames_sent = 0
            last_fps_time = now

        time.sleep(1 / 30)

finally:
    pipeline.stop()
    cleanup()
    udp_sock.close()
    print("[✔] Shutdown complete.")
