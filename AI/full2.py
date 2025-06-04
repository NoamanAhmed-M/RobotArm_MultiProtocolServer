import cv2
import numpy as np
import pyrealsense2 as rs
import time
import heapq
import Jetson.GPIO as GPIO
from yoloDet import YoloTRT

# YOLO model
model = YoloTRT(
    library="yolov5/buildMM/libmyplugins.so",
    engine="yolov5/buildMM/bestt.engine",
    conf=0.5,
    yolo_ver="v5"
)

# === GPIO Setup ===
IN1 = 7
IN2 = 11
ENA = 13
IN3 = 27
IN4 = 16
ENB = 18

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

def motor_a_forward(speed, duration):  # Right
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    software_pwm(ENA, speed, 100, duration)

def motor_a_backward(speed, duration):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    software_pwm(ENA, speed, 100, duration)

def motor_b_forward(speed, duration):  # Left
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
    duration = 0.3
    if dx == 1 and dy == 0:  # Right
        motor_a_forward(speed, duration)
        motor_b_backward(speed, duration)
    elif dx == -1 and dy == 0:  # Left
        motor_a_backward(speed, duration)
        motor_b_forward(speed, duration)
    elif dx == 0 and dy == -1:  # Forward
        motor_a_forward(speed, duration)
        motor_b_forward(speed, duration)
    elif dx == 0 and dy == 1:  # Backward
        motor_a_backward(speed, duration)
        motor_b_backward(speed, duration)
    stop_all()
    time.sleep(0.1)

# === Depth & A* ===
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

# === RealSense ===
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

                # رسم الخريطة والمسار
                map_vis = np.ones((200, 200, 3), dtype=np.uint8) * 255
                cell_size = 10
                for y in range(20):
                    for x in range(20):
                        color = (255, 255, 255)
                        if grid_map[y][x] == 1:
                            color = (0, 0, 255)
                        cv2.rectangle(map_vis, (x*cell_size, y*cell_size),
                                      ((x+1)*cell_size, (y+1)*cell_size), color, -1)
                for (x, y) in path:
                    cv2.rectangle(map_vis, (x*cell_size, y*cell_size),
                                  ((x+1)*cell_size, (y+1)*cell_size), (0, 255, 255), -1)
                cv2.rectangle(map_vis, (start[0]*cell_size, start[1]*cell_size),
                              ((start[0]+1)*cell_size, (start[1]+1)*cell_size), (255, 0, 0), -1)
                cv2.rectangle(map_vis, (goal[0]*cell_size, goal[1]*cell_size),
                              ((goal[0]+1)*cell_size, (goal[1]+1)*cell_size), (0, 255, 0), -1)
                frame[0:200, 0:200] = cv2.resize(map_vis, (200, 200))

                # تنفيذ الحركة خطوة بخطوة
                for i in range(len(path)-1):
                    dx = path[i+1][0] - path[i][0]
                    dy = path[i+1][1] - path[i][1]
                    move_step(dx, dy)

                # رسم معلومات الكائن
                label = f"{det['class']} {det['conf']:.2f}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(frame, f"{depth:.2f} m", (cx, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        cv2.imshow("YOLOv5 + RealSense + A* Navigation", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    stop_all()
    GPIO.cleanup()
    pipeline.stop()
    cv2.destroyAllWindows()
