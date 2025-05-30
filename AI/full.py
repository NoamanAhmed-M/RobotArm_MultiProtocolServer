# YOLO + RealSense + A* Navigation in a Small Room
# Assumptions:
# - Jetson Nano with RealSense camera
# - L298N motor driver for two wheels
# - YOLO inference is working
# - No preloaded map; grid is built in real time

import cv2
import numpy as np
import pyrealsense2 as rs
import time
import math
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from yoloDet import YoloTRT

# ===== Motor Control Setup (GPIO) =====
import Jetson.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)

ENA, ENB = 32, 33
IN1, IN2, IN3, IN4 = 21, 22, 23, 24
GPIO.setup([ENA, ENB, IN1, IN2, IN3, IN4], GPIO.OUT)
pwm_a = GPIO.PWM(ENA, 100)
pwm_b = GPIO.PWM(ENB, 100)
pwm_a.start(0)
pwm_b.start(0)

speed = 0.2  # m/s
angular_speed = math.radians(90)  # rad/s
cell_size = 0.1  # meters

# Robot position
position = {'x': 0.0, 'y': 0.0, 'theta': 0.0}

# === Movement Wrappers ===
def stop():
    GPIO.output([IN1, IN2, IN3, IN4], GPIO.LOW)
    pwm_a.ChangeDutyCycle(0)
    pwm_b.ChangeDutyCycle(0)

def move_forward(duration=0.5):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_a.ChangeDutyCycle(60)
    pwm_b.ChangeDutyCycle(60)
    time.sleep(duration)
    stop()
    dx = speed * duration * math.cos(position['theta'])
    dy = speed * duration * math.sin(position['theta'])
    position['x'] += dx
    position['y'] += dy

def turn_left(duration=0.5):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_a.ChangeDutyCycle(50)
    pwm_b.ChangeDutyCycle(50)
    time.sleep(duration)
    stop()
    position['theta'] += angular_speed * duration

def turn_right(duration=0.5):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    pwm_a.ChangeDutyCycle(50)
    pwm_b.ChangeDutyCycle(50)
    time.sleep(duration)
    stop()
    position['theta'] -= angular_speed * duration

# === Depth Utilities ===
def get_center_depth(depth_frame, cx, cy, k=3):
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
    filtered = [v for v in values if abs(v - median) < 0.1]
    return np.mean(filtered) if filtered else median

# === Map Builder ===
def build_occupancy_grid(depth_frame, grid_size=20):
    grid = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
    for i in range(grid_size):
        for j in range(grid_size):
            x = int(depth_frame.get_width() * (i / grid_size))
            y = int(depth_frame.get_height() * (j / grid_size))
            d = depth_frame.get_distance(x, y)
            if 0 < d < 0.3:
                grid[j][i] = 1
    return grid

# === Object Projection to Grid ===
def object_to_grid(cx, cy, depth, grid_size=20):
    center = grid_size // 2
    dx = int((depth * math.cos(position['theta'])) / cell_size)
    dy = int((depth * math.sin(position['theta'])) / cell_size)
    gx = center + dx
    gy = center + dy
    return min(max(gx, 0), grid_size - 1), min(max(gy, 0), grid_size - 1)

# === Path Following ===
def follow_path(path):
    for idx in range(1, len(path)):
        x1, y1 = path[idx - 1]
        x2, y2 = path[idx]
        dx, dy = x2 - x1, y2 - y1
        angle = math.atan2(dy, dx)
        angle_diff = angle - position['theta']
        if angle_diff > 0:
            turn_left(abs(angle_diff) / angular_speed)
        else:
            turn_right(abs(angle_diff) / angular_speed)
        move_forward(cell_size / speed)

# === Setup Camera & YOLO ===
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 424, 240, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 30)
profile = pipeline.start(config)

model = YoloTRT(
    library="yolov5/buildM/libmyplugins.so",
    engine="yolov5/buildM/best.engine",
    conf=0.5,
    yolo_ver="v5"
)

align = rs.align(rs.stream.color)

try:
    while True:
        frames = pipeline.wait_for_frames()
        aligned = align.process(frames)
        depth_frame = aligned.get_depth_frame()
        color_frame = aligned.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        frame = np.asanyarray(color_frame.get_data())
        detections, _ = model.Inference(frame)

        if detections:
            det = detections[0]
            x1, y1, x2, y2 = map(int, det['box'])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            depth = get_center_depth(depth_frame, cx, cy)
            grid_map = build_occupancy_grid(depth_frame)
            gx, gy = object_to_grid(cx, cy, depth)

            grid = Grid(matrix=grid_map)
            start = grid.node(grid.width // 2, grid.height // 2)
            target = grid.node(gx, gy)
            finder = AStarFinder()
            path, _ = finder.find_path(start, target, grid)

            for i in range(len(path) - 1):
                x1, y1 = path[i]
                x2, y2 = path[i + 1]
                pt1 = (x1 * 20, y1 * 20)
                pt2 = (x2 * 20, y2 * 20)
                cv2.line(frame, pt1, pt2, (255, 0, 0), 2)

            cv2.circle(frame, (cx, cy), 4, (0, 255, 255), -1)
            follow_path(path)
            stop()

        cv2.imshow("Navigation View", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    GPIO.cleanup()
    cv2.destroyAllWindows()
