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
UDP_IP = '192.168.43.114'       # Replace with viewer/server IP
UDP_PORT = 5005
MAX_DGRAM = 65000
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# === TCP Control Setup ===
TCP_IP = '192.168.43.114'        # Replace with Web Server IP
TCP_PORT = 5555
CLIENT_NAME = "RobotArm"
RECONNECT_DELAY = 5

# Movement flag (shared between threads)
should_move = threading.Event()  # Starts off as False

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

# Set RealSense depth visual preset
depth_sensor = profile.get_device().first_depth_sensor()
if depth_sensor.supports(rs.option.visual_preset):
    try:
        depth_sensor.set_option(rs.option.visual_preset, 2.0)
    except Exception as e:
        print(f"[!] Depth Preset Error: {e}")

# Enable auto exposure for color stream
sensors = profile.get_device().query_sensors()
if len(sensors) > 1 and sensors[1].supports(rs.option.enable_auto_exposure):
    sensors[1].set_option(rs.option.enable_auto_exposure, 1)

# Align depth with color frame
align = rs.align(rs.stream.color)

# === Helper: Get average depth around point (cx, cy) ===
def get_average_depth(depth_frame, cx, cy, k=7):
    values = []
    for dx in range(-k//2, k//2 + 1):
        for dy in range(-k//2, k//2 + 1):
            x, y = cx + dx, cy + dy
            if 0 <= x < depth_frame.get_width() and 0 <= y < depth_frame.get_height():
                d = depth_frame.get_distance(x, y)
                if 0 < d < 5:
                    values.append(d)
    if not values:
        return 0
    median = np.median(values)
    filtered = [v for v in values if abs(v - median) < 0.3]
    return np.mean(filtered) if filtered else median

# === TCP Client Thread ===
def start_tcp_client():
    def receive_messages(sock):
        while True:
            try:
                data = sock.recv(4096)
                if not data:
                    print("[RobotArm] ❌ Server closed connection")
                    break

                message = json.loads(data.decode('utf-8'))
                print(f"[SERVER -> RobotArm] {message}")

                if message.get("type") == "command":
                    if message.get("value") is True:
                        should_move.set()
                        print("[RobotArm] ✅ Movement ENABLED (direct)")
                    else:
                        should_move.clear()
                        print("[RobotArm] ⛔ Movement DISABLED (direct)")
                elif message.get("type") == "status" and "Command received" in message.get("msg", ""):
                    try:
                        embedded = ast.literal_eval(message["msg"].split("Command received: ")[1])
                        if embedded.get("type") == "command":
                            if embedded.get("value") is True:
                                should_move.set()
                                print("[RobotArm] ✅ Movement ENABLED (embedded)")
                            else:
                                should_move.clear()
                                print("[RobotArm] ⛔ Movement DISABLED (embedded)")
                    except Exception as e:
                        print(f"[RobotArm] ⚠️ Failed to parse embedded command: {e}")

            except Exception as e:
                print(f"[RobotArm] ❌ Receiving failed: {e}")
                break

    def send_status_messages(sock):
        while True:
            try:
                message = {
                    "type": "status",
                    "msg": "Arm ready",
                    "position": [10, 20, 30]
                }
                sock.send(json.dumps(message).encode('utf-8'))
                print("[RobotArm -> Server] ✅ Sent status update")
                time.sleep(5)
            except Exception as e:
                print(f"[RobotArm] ❌ Sending failed: {e}")
                break

    while True:
        try:
            print(f"[RobotArm] 🔌 Connecting to {TCP_IP}:{TCP_PORT}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((TCP_IP, TCP_PORT))
            print("[RobotArm] ✅ Connected to server")
            sock.send((CLIENT_NAME + "\n").encode('utf-8'))

            threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()
            threading.Thread(target=send_status_messages, args=(sock,), daemon=True).start()

            while True:
                if sock._closed:
                    break
                time.sleep(1)

        except Exception as e:
            print(f"[RobotArm] ❌ Connection failed: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
            print(f"[RobotArm] 🔁 Reconnecting in {RECONNECT_DELAY} seconds...")
            time.sleep(RECONNECT_DELAY)

# === Start TCP in background ===
threading.Thread(target=start_tcp_client, daemon=True).start()

# === Main Processing Loop ===
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

            label = f"{det['class']} {det['conf']:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(frame, f"{distance:.2f} m", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            offset = cx - center_x
            threshold = w // 10

            if should_move.is_set():
                if 0.4 < distance < 2.0:
                    if offset < -threshold:
                        turn_left_step(20, 50, 0.1)
                    elif offset > threshold:
                        turn_right_step(20, 50, 0.1)
                    else:
                        move_forward_step(20, 50, 0.1)
                else:
                    stop_all()
            else:
                stop_all()
            break  # Only handle first detected object

        # FPS display
        cv2.putText(frame, f"FPS: {1/t:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Stream over UDP
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
        if now - last_fps_time >= 5.0:
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
