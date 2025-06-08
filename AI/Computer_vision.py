import sys
import cv2
import numpy as np
import pyrealsense2 as rs
import socket
import struct
import time
import json
import threading
from collections import deque
from motor_control import move_forward_step, turn_left_step, turn_right_step, stop_all, cleanup

# === Network Setup ===
UDP_IP = '192.168.43.114'
UDP_PORT = 5005
MAX_DGRAM = 65000
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

TCP_IP = '192.168.43.114'
TCP_PORT = 5555
CLIENT_NAME = "RobotArm"
RECONNECT_DELAY = 5
should_move = threading.Event()

# === RealSense Camera ===
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 424, 240, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 30)
profile = pipeline.start(config)
align = rs.align(rs.stream.color)

def get_average_depth(depth_frame, cx, cy, k=5):
    values = []
    for dx in range(-k//2, k//2+1):
        for dy in range(-k//2, k//2+1):
            x, y = cx + dx, cy + dy
            if 0 <= x < depth_frame.get_width() and 0 <= y < depth_frame.get_height():
                d = depth_frame.get_distance(x, y)
                if 0.2 < d < 5:
                    values.append(d)
    return np.mean(values) if values else 0

def start_tcp_receiver():
    def receive_commands(sock):
        while True:
            try:
                data = sock.recv(4096)
                if not data:
                    break
                message = json.loads(data.decode('utf-8'))
                if message.get("type") == "command":
                    should_move.set() if message.get("value") else should_move.clear()
            except:
                break

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((TCP_IP, TCP_PORT))
            sock.send((CLIENT_NAME + "\n").encode('utf-8'))
            receive_commands(sock)
        except:
            time.sleep(RECONNECT_DELAY)

threading.Thread(target=start_tcp_receiver, daemon=True).start()

# === Main Loop ===
frame_num = 0
last_process_time = 0
cooldown_timer = 0
shape_detected_recently = False
depth_buffer = deque(maxlen=5)

try:
    while True:
        frames = pipeline.wait_for_frames()
        aligned_frames = align.process(frames)
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        color_image = np.asanyarray(color_frame.get_data())
        display_image = color_image.copy()
        gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        now = time.time()
        if now - last_process_time >= 0.5:
            last_process_time = now
            detected = False

            if cooldown_timer > 0:
                cooldown_timer -= 1

            # Detect black cylinder
            circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, 1, 40,
                                       param1=50, param2=30, minRadius=15, maxRadius=60)
            if circles is not None:
                for circle in circles[0, :1]:
                    cx, cy, radius = map(int, circle)
                    distance = get_average_depth(depth_frame, cx, cy)
                    depth_buffer.append(distance)
                    smoothed_depth = np.mean(depth_buffer)

                    if 0.2 < smoothed_depth < 2.0:
                        cv2.circle(display_image, (cx, cy), radius, (0, 0, 255), 2)
                        if should_move.is_set() and cooldown_timer == 0:
                            w = color_image.shape[1]
                            if cx < w // 3:
                                turn_left_step(20, 50, 0.1)
                            elif cx > 2 * w // 3:
                                turn_right_step(20, 50, 0.1)
                            else:
                                move_forward_step(20, 50, 0.1)
                            detected = True
                            cooldown_timer = 2
                            break

            # Detect square with hole
            if not detected:
                _, thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    approx = cv2.approxPolyDP(cnt, 0.04 * cv2.arcLength(cnt, True), True)
                    area = cv2.contourArea(cnt)
                    if len(approx) == 4 and area > 1000:
                        x, y, w, h = cv2.boundingRect(approx)
                        cx, cy = x + w // 2, y + h // 2
                        distance = get_average_depth(depth_frame, cx, cy)
                        depth_buffer.append(distance)
                        smoothed_depth = np.mean(depth_buffer)

                        if 0.2 < smoothed_depth < 2.0:
                            cv2.rectangle(display_image, (x, y), (x + w, y + h), (255, 0, 0), 2)
                            if should_move.is_set() and cooldown_timer == 0:
                                img_w = color_image.shape[1]
                                if cx < img_w // 3:
                                    turn_left_step(20, 50, 0.1)
                                elif cx > 2 * img_w // 3:
                                    turn_right_step(20, 50, 0.1)
                                else:
                                    move_forward_step(20, 50, 0.1)
                                cooldown_timer = 2
                                break

        # === UDP Frame Streaming ===
        resized = cv2.resize(display_image, (640, 480))
        _, encoded_img = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        img_data = encoded_img.tobytes()
        chunks = [img_data[i:i + MAX_DGRAM - 8] for i in range(0, len(img_data), MAX_DGRAM - 8)]
        for chunk in chunks:
            header = struct.pack('>II', frame_num, len(chunks))
            udp_sock.sendto(header + chunk, (UDP_IP, UDP_PORT))
        frame_num += 1

        time.sleep(1 / 15)  # Limit to 15 FPS

finally:
    pipeline.stop()
    cleanup()
    udp_sock.close()
    print("[✔] Shutdown complete.")
