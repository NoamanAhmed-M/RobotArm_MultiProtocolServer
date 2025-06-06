# main.py (A* version with non-blocking movement + visualization)
import cv2
import numpy as np
import heapq
from collections import deque
from yolo_detection import detect_objects
from realsense_processing import get_aligned_frames, stop_pipeline, get_center_depth
from movement import execute_path, cleanup

# A* Pathfinding Utilities
class Node:
    def __init__(self, x, y, cost=0, heuristic=0, parent=None):
        self.x = x
        self.y = y
        self.cost = cost
        self.heuristic = heuristic
        self.parent = parent
    def __lt__(self, other):
        return (self.cost + self.heuristic) < (other.cost + other.heuristic)

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

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

def map_object_to_grid(cx, cy, frame_width, frame_height, grid_size=20):
    fx = (cx - frame_width // 2) / frame_width
    fy = (cy - frame_height // 2) / frame_height
    dx = int(fx * grid_size)
    dy = int(fy * grid_size)
    gx = grid_size // 2 + dx
    gy = grid_size // 2 + dy
    return min(max(gx, 0), grid_size - 1), min(max(gy, 0), grid_size - 1)

# Movement queue for incremental execution
movement_queue = deque()
path_ready = False

try:
    while True:
        depth_frame, color_frame = get_aligned_frames()
        if not depth_frame or not color_frame:
            continue

        frame = np.asanyarray(color_frame.get_data())
        detections = detect_objects(frame)

        if detections:
            det = detections[0]
            x1, y1, x2, y2 = map(int, det['box'])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            depth = get_center_depth(depth_frame, cx, cy)
            frame_h, frame_w = frame.shape[:2]

            if depth > 0:
                grid_map = build_occupancy_grid(depth_frame)
                gx, gy = map_object_to_grid(cx, cy, frame_w, frame_h)
                start = (len(grid_map[0])//2, len(grid_map)//2)
                goal = (gx, gy)
                path = astar(grid_map, start, goal)

                # Visualize path
                for i in range(len(path)-1):
                    x1g, y1g = path[i]
                    x2g, y2g = path[i+1]
                    pt1 = (int((x1g / 20) * frame_w), int((y1g / 20) * frame_h))
                    pt2 = (int((x2g / 20) * frame_w), int((y2g / 20) * frame_h))
                    cv2.arrowedLine(frame, pt1, pt2, (255, 0, 0), 2, tipLength=0.4)

                if len(path) > 1:
                    movement_queue = deque(path)
                    path_ready = True

            label = f"{det['class']} {det['conf']:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(frame, f"{depth:.2f} m", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        # Execute movement incrementally
        if path_ready and len(movement_queue) > 1:
            step_start = movement_queue.popleft()
            step_next = movement_queue[0]
            execute_path([step_start, step_next])
        elif path_ready and len(movement_queue) <= 1:
            path_ready = False

        cv2.imshow("YOLO + A* Path + Movement", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    stop_pipeline()
    cv2.destroyAllWindows()
    cleanup()
