# === Optimized Jetson YOLO + Depth + Motor Control ===
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

# Shared event
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
config.enable_stream(rs.stream.depth, 320, 240, rs.format.z16, 15)
config.enable_stream(rs.stream.color, 320, 240, rs.format.bgr8, 15)
profile = pipeline.start(config)

# Configure depth sensor
depth_sensor = profile.get_device().first_depth_sensor()
if depth_sensor.supports(rs.option.visual_preset):
    try:
        depth_sensor.set_option(rs.option.visual_preset, 2.0)
    except Exception as e:
        print(f"[!] Depth Preset Error: {e}")

# Auto-exposure for color
sensors = profile.get_device().query_sensors()
if len(sensors) > 1 and sensors[1].supports(rs.option.enable_auto_exposure):
    sensors[1].set_option(rs.option.enable_auto_exposure, 1)

# Depth alignment
align = rs.align(rs.stream.color)

# === Helper ===
def get_average_depth(depth_frame, cx, cy, k=5):
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

# === TCP Communication ===
def start_tcp_client():
    def receive_messages(sock):
        while True:
            try:
                data = sock.recv(4096)
                if not data:
                    print("[RobotArm] Server closed connection")
                    break

                message = json.loads(data.decode('utf-8'))
                print(f"[SERVER -> RobotArm] {message}")

                if message.get("type") == "command":
                    should_move.set() if message.get("value") else should_move.clear()
                elif message.get("type") == "status" and "Command received" in message.get("msg", ""):
                    try:
                        embedded = ast.literal_eval(message["msg"].split("Command received: ")[1])
                        if embedded.get("type") == "command":
                            should_move.set() if embedded.get("value") else should_move.clear()
                    except Exception as e:
                        print(f"[RobotArm] Failed to parse embedded command: {e}")
            except Exception as e:
                print(f"[RobotArm] Receiving failed: {e}")
                break

    def send_status_messages(sock):
        while True:
            try:
                message = {"type": "status", "msg": "Arm ready", "position": [10, 20, 30]}
                sock.send(json.dumps(message).encode('utf-8'))
                time.sleep(10)
            except:
                break

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((TCP_IP, TCP_PORT))
            sock.send((CLIENT_NAME + "\n").encode('utf-8'))
            threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()
            send_status_messages(sock)
        except Exception as e:
            print(f"[RobotArm] TCP connection failed: {e}")
        finally:
            sock.close()
            time.sleep(RECONNECT_DELAY)

threading.Thread(target=start_tcp_client, daemon=True).start()

# === Main Loop ===
frame_num = 0
last_fps_time = time.time()
frames_sent = 0
last_detection_time = 0
cached_detections = []
last_udp_time = 0

try:
    while True:
        frames = pipeline.wait_for_frames()
        aligned = align.process(frames)
        depth_frame = aligned.get_depth_frame()
        color_frame = aligned.get_color_frame()

        if not depth_frame or not color_frame:
            continue

        frame = np.asanyarray(color_frame.get_data())
        h, w, _ = frame.shape
        center_x = w // 2

        # Run detection every 0.5s
        if time.time() - last_detection_time >= 0.5:
            resized_frame = cv2.resize(frame, (320, 320))
            cached_detections, t = model.Inference(resized_frame)
            scale_x = frame.shape[1] / 320
            scale_y = frame.shape[0] / 320
            for d in cached_detections:
                d['box'] = [int(coord * scale) for coord, scale in zip(d['box'], [scale_x, scale_y, scale_x, scale_y])]
            last_detection_time = time.time()

        for det in cached_detections:
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
            break

        # FPS Text
        cv2.putText(frame, f"FPS: {1/t:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Send UDP frame every ~15 fps
        if time.time() - last_udp_time >= 1 / 15:
            resized = cv2.resize(frame, (640, 480))
            _, encoded = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            img_data = encoded.tobytes()
            chunks = [img_data[i:i+MAX_DGRAM-8] for i in range(0, len(img_data), MAX_DGRAM-8)]
            for chunk in chunks:
                header = struct.pack('>II', frame_num, len(chunks))
                udp_sock.sendto(header + chunk, (UDP_IP, UDP_PORT))
            last_udp_time = time.time()

        frame_num += 1
        frames_sent += 1

        if time.time() - last_fps_time >= 5.0:
            fps = frames_sent / (time.time() - last_fps_time)
            print(f"[UDP] FPS: {fps:.2f}")
            last_fps_time = time.time()
            frames_sent = 0

        time.sleep(1 / 30)

finally:
    pipeline.stop()
    cleanup()
    udp_sock.close()
    print("[✔] Shutdown complete.")
