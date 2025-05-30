import cv2
import numpy as np
import pyrealsense2 as rs
from yoloDet import YoloTRT
import time
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder

# Load YOLO-TensorRT model
model = YoloTRT(
    library="yolov5/buildM/libmyplugins.so",
    engine="yolov5/buildM/best.engine",
    conf=0.5,
    yolo_ver="v5"
)

# Depth estimation around center
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

# Build local occupancy grid from depth frame
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

# Map object detection to grid coordinates
def map_object_to_grid(cx, cy, depth, frame_width, frame_height, grid_size=20):
    fx = (cx - frame_width // 2) / frame_width
    fy = (cy - frame_height // 2) / frame_height
    dx = int(fx * grid_size)
    dy = int(fy * grid_size)

    gx = grid_size // 2 + dx
    gy = grid_size // 2 + dy
    return min(max(gx, 0), grid_size - 1), min(max(gy, 0), grid_size - 1)

# Initialize RealSense camera
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 424, 240, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 30)
profile = pipeline.start(config)

# Set high accuracy preset
depth_sensor = profile.get_device().first_depth_sensor()
if depth_sensor.supports(rs.option.visual_preset):
    try:
        depth_sensor.set_option(rs.option.visual_preset, 2.0)
        print("Visual Preset set to High Accuracy")
    except:
        pass

# Enable auto exposure
sensors = profile.get_device().query_sensors()
if len(sensors) > 1 and sensors[1].supports(rs.option.enable_auto_exposure):
    sensors[1].set_option(rs.option.enable_auto_exposure, 1)

# Align depth to color stream
align = rs.align(rs.stream.color)

# Variables for periodic detection
last_detection_time = 0
detection_interval = 0.5  # seconds
results = []

try:
    while True:
        frames = pipeline.wait_for_frames()
        aligned = align.process(frames)
        depth_frame = aligned.get_depth_frame()
        color_frame = aligned.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        frame = np.asanyarray(color_frame.get_data())

        current_time = time.time()
        if current_time - last_detection_time >= detection_interval:
            detections, _ = model.Inference(frame)
            new_results = []
            for det in detections:
                x1, y1, x2, y2 = map(int, det['box'])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                depth = get_center_depth(depth_frame, cx, cy)
                new_results.append({
                    'box': (x1, y1, x2, y2),
                    'class': det['class'],
                    'conf': det['conf'],
                    'depth': depth
                })
            results = new_results
            last_detection_time = current_time

        # Draw latest results
        for r in results:
            x1, y1, x2, y2 = r['box']
            label = f"{r['class']} {r['conf']:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            if r['depth'] > 0:
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                cv2.putText(frame, f"{r['depth']:.2f} m", (cx, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                # Build grid and draw A* path
                grid_map = build_occupancy_grid(depth_frame)
                frame_h, frame_w = frame.shape[:2]
                gx, gy = map_object_to_grid(cx, cy, r['depth'], frame_w, frame_h)

                grid = Grid(matrix=grid_map)
                start = grid.node(grid.width // 2, grid.height // 2)
                end = grid.node(gx, gy)
                finder = AStarFinder()
                path, _ = finder.find_path(start, end, grid)

                for i in range(len(path) - 1):
                    x1, y1 = path[i]
                    x2, y2 = path[i + 1]
                    pt1 = (int((x1 / 20) * frame_w), int((y1 / 20) * frame_h))
                    pt2 = (int((x2 / 20) * frame_w), int((y2 / 20) * frame_h))
                    cv2.line(frame, pt1, pt2, (255, 0, 0), 2)

        # Display stream
        cv2.imshow("YOLOv5 + RealSense Stream", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
