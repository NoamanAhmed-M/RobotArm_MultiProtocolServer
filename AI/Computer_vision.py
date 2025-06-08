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
                if 0.2 < d < 2.0:
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
            cooldown_timer = max(0, cooldown_timer - 1)

            # === Detect black cylinder ===
            _, dark_thresh = cv2.threshold(blurred, 50, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(dark_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                perimeter = cv2.arcLength(cnt, True)
                if perimeter == 0: continue
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                if area > 300 and 0.7 < circularity < 1.3:
                    (x, y, w, h) = cv2.boundingRect(cnt)
                    cx, cy = x + w // 2, y + h // 2
                    distance = get_average_depth(depth_frame, cx, cy)
                    depth_buffer.append(distance)
                    mean_depth = np.mean(depth_buffer)
                    cv2.circle(display_image, (cx, cy), int(w/2), (0, 0, 255), 2)
                    if should_move.is_set() and cooldown_timer == 0 and mean_depth > 0:
                        width = color_image.shape[1]
                        if cx < width // 3:
                            turn_left_step(20, 50, 0.1)
                        elif cx > 2 * width // 3:
                            turn_right_step(20, 50, 0.1)
                        else:
                            move_forward_step(20, 50, 0.1)
                        cooldown_timer = 2
                        detected = True
                        break

            # === Detect white square with a circular hole ===
            if not detected:
                _, light_thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(light_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    approx = cv2.approxPolyDP(cnt, 0.04 * cv2.arcLength(cnt, True), True)
                    area = cv2.contourArea(cnt)
                    if len(approx) == 4 and area > 1000:
                        x, y, w, h = cv2.boundingRect(approx)
                        cx, cy = x + w // 2, y + h // 2
                        square_mask = np.zeros_like(gray)
                        cv2.drawContours(square_mask, [cnt], -1, 255, -1)
                        inner = cv2.bitwise_and(blurred, blurred, mask=square_mask)
                        _, hole_thresh = cv2.threshold(inner, 60, 255, cv2.THRESH_BINARY_INV)
                        holes, _ = cv2.findContours(hole_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                        for hcnt in holes:
                            h_area = cv2.contourArea(hcnt)
                            h_perim = cv2.arcLength(hcnt, True)
                            if h_perim == 0: continue
                            h_circ = 4 * np.pi * h_area / (h_perim * h_perim)
                            if h_area < 500 and 0.7 < h_circ < 1.3:
                                distance = get_average_depth(depth_frame, cx, cy)
                                depth_buffer.append(distance)
                                mean_depth = np.mean(depth_buffer)
                                cv2.rectangle(display_image, (x, y), (x + w, y + h), (255, 0, 0), 2)
                                if should_move.is_set() and cooldown_timer == 0 and mean_depth > 0:
                                    img_w = color_image.shape[1]
                                    if cx < img_w // 3:
                                        turn_left_step(20, 50, 0.1)
                                    elif cx > 2 * img_w // 3:
                                        turn_right_step(20, 50, 0.1)
                                    else:
                                        move_forward_step(20, 50, 0.1)
                                    cooldown_timer = 2
                                    break

        # === UDP Stream ===
        resized = cv2.resize(display_image, (640, 480))
        _, encoded_img = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        img_data = encoded_img.tobytes()
        chunks = [img_data[i:i + MAX_DGRAM - 8] for i in range(0, len(img_data), MAX_DGRAM - 8)]
        for chunk in chunks:
            header = struct.pack('>II', frame_num, len(chunks))
            udp_sock.sendto(header + chunk, (UDP_IP, UDP_PORT))
        frame_num += 1

        time.sleep(1 / 15)

finally:
    pipeline.stop()
    cleanup()
    udp_sock.close()
    print("[✔] Shutdown complete.")
