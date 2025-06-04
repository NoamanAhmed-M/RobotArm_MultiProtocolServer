# Full integration of YOLO + RealSense + A* pathfinding + GPIO motor control on Jetson Nano

import cv2
import numpy as np
import pyrealsense2 as rs
import time
import heapq
import Jetson.GPIO as GPIO
from yoloDet import YoloTRT

# === GPIO Setup ===
IN1 = 9    # Pin 21
IN2 = 10   # Pin 22
ENA = 18   # Pin 32
IN3 = 11   # Pin 23
IN4 = 8    # Pin 24
ENB = 19   # Pin 33

GPIO.setmode(GPIO.BCM)
for pin in [IN1, IN2, ENA, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

def software_pwm(pin, duty_cycle, frequency, duration):
    period = 1.0 / frequency
    on_time = period * duty_cycle
    off_time = period * (1 - duty_cycle)
    end_time = time.time() + duration
    while time.time() < end_time:
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(on_time)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(off_time)

def motor_a_forward(speed, duration):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    software_pwm(ENA, speed, 100, duration)

def motor_a_backward(speed, duration):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    software_pwm(ENA, speed, 100, duration)

def motor_b_forward(speed, duration):
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    software_pwm(ENB, speed, 100, duration)

def motor_b_backward(speed, duration):
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    software_pwm(ENB, speed, 100, duration)

def stop_all():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    GPIO.output(ENA, GPIO.LOW)
    GPIO.output(ENB, GPIO.LOW)

def move_step(dx, dy):
    speed = 0.4
    duration = 0.5
    if dx == 1 and dy == 0:
        motor_a_forward(speed, duration)
        motor_b_backward(speed, duration)
    elif dx == -1 and dy == 0:
        motor_a_backward(speed, duration)
        motor_b_forward(speed, duration)
    elif dx == 0 and dy == 1:
        motor_a_backward(speed, duration)
        motor_b_backward(speed, duration)
    elif dx == 0 and dy == -1:
        motor_a_forward(speed, duration)
        motor_b_forward(speed, duration)
    stop_all()
    time.sleep(0.1)

# === YOLO Model ===
model = YoloTRT(
    library="yolov5/buildM/libmyplugins.so",
    engine="yolov5/buildM/best.engine",
    conf=0.5,
    yolo_ver="v5"
)

# === Helper Functions ===
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

class Node:
    def __init__(self, x, y, cost=0, heuristic=0, parent=None):
        self.x = x
        self.y = y
        self.cost = cost
        self.heuristic = heuristic
        self.parent = parent
    def __lt__(self, other):
        return (self.cost + self.heuristic) < (other.cost + other.heuristic)

def astar(grid, start, goal):
    open_set = []
    heapq.heappush(open_set, Node(*start, 0, heuristic(start, goal)))
    visited = set()
    while open_set:
        current = heapq.heappop(open_set)
        if (current.x, current.y) == goal:
            return reconstruct_path(current)
        visited.add((current.x, current.y))
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = current.x + dx, current.y + dy
            if 0 <= nx < len(grid[0]) and 0 <= ny < len(grid):
                if grid[ny][nx] == 1 or (nx, ny) in visited:
                    continue
                neighbor = Node(nx, ny, current.cost + 1, heuristic((nx, ny), goal), current)
                heapq.heappush(open_set, neighbor)
    return []

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def reconstruct_path(node):
    path = []
    while node:
        path.append((node.x, node.y))
        node = node.parent
    return path[::-1]

def build_occupancy_grid(depth_frame, grid_size=20):
    grid = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
    width = depth_frame.get_width()
    height = depth_frame.get_height()
    for i in range(grid_size):
        for j in range(grid_size):
            x = int(width * (i / grid_size))
            y = int(height * (j / grid_size))
            d = depth_frame.get_distance(x, y)
            if 0 < d < 0.3:
                grid[j][i] = 1
    return grid

def map_object_to_grid(cx, cy, depth, frame_width, frame_height, grid_size=20):
    fx = (cx - frame_width // 2) / frame_width
    fy = (cy - frame_height // 2) / frame_height
    dx = int(fx * grid_size)
    dy = int(fy * grid_size)
    gx = grid_size // 2 + dx
    gy = grid_size // 2 + dy
    return min(max(gx, 0), grid_size - 1), min(max(gy, 0), grid_size - 1)

# === RealSense Init ===
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 424, 240, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 30)
profile = pipeline.start(config)
align = rs.align(rs.stream.color)

# === Main Loop ===
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
            frame_h, frame_w = frame.shape[:2]

            if depth > 0:
                grid_map = build_occupancy_grid(depth_frame)
                gx, gy = map_object_to_grid(cx, cy, depth, frame_w, frame_h)
                start = (len(grid_map[0])//2, len(grid_map)//2)
                goal = (gx, gy)
                path = astar(grid_map, start, goal)

                for i in range(len(path)-1):
                    dx = path[i+1][0] - path[i][0]
                    dy = path[i+1][1] - path[i][1]
                    move_step(dx, dy)

                stop_all()
                time.sleep(1)
                break

finally:
    stop_all()
    GPIO.cleanup()
    pipeline.stop()
    cv2.destroyAllWindows()
