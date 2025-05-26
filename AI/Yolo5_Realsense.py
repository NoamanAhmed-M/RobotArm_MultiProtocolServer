#3
import sys
import cv2
import numpy as np
import pyrealsense2 as rs
from yoloDet import YoloTRT

# Load YOLO-TensorRT model
model = YoloTRT(
    library="yolov5/buildM/libmyplugins.so",
    engine="yolov5/buildM/best.engine",
    conf=0.5,
    yolo_ver="v5"
)

# Helper function to get filtered average depth
def get_average_depth(depth_frame, cx, cy, k=7):
    depth_values = []
    for dx in range(-k // 2, k // 2 + 1):
        for dy in range(-k // 2, k // 2 + 1):
            x = cx + dx
            y = cy + dy
            if 0 <= x < depth_frame.get_width() and 0 <= y < depth_frame.get_height():
                d = depth_frame.get_distance(x, y)
                if d > 0:
                    depth_values.append(d)
    if not depth_values:
        return 0
    depth_array = np.array(depth_values)
    median = np.median(depth_array)
    filtered = depth_array[np.abs(depth_array - median) < 0.3]  # Remove outliers >30cm
    return np.mean(filtered) if filtered.size > 0 else median

# Initialize RealSense pipeline
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 424, 240, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 30)
profile = pipeline.start(config)

# Set high accuracy preset safely
depth_sensor = profile.get_device().first_depth_sensor()
if depth_sensor.supports(rs.option.visual_preset):
    try:
        preset_index = 2.0  # High Accuracy
        depth_sensor.set_option(rs.option.visual_preset, preset_index)
        name = depth_sensor.get_option_value_description(rs.option.visual_preset, preset_index)
        print(f"Visual Preset set to: {name}")
    except Exception as e:
        print(f"Failed to set visual preset: {e}")

# Enable auto exposure on color sensor
sensors = profile.get_device().query_sensors()
if len(sensors) > 1 and sensors[1].supports(rs.option.enable_auto_exposure):
    sensors[1].set_option(rs.option.enable_auto_exposure, 1)

# Align depth to color
align = rs.align(rs.stream.color)

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

        for det in detections:
            x1, y1, x2, y2 = map(int, det['box'])
            cls = det['class']
            conf = det['conf']
            label = f"{cls} {conf:.2f}"
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            distance = get_average_depth(depth_frame, cx, cy, k=7)

            if 0 < distance <= 5.0:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(frame, f"{distance:.2f} m", (cx, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Show FPS
        cv2.putText(frame, f"FPS: {1/t:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Show image
        cv2.imshow("YOLOv5 + RealSense Distance", frame)

        # Optional: depth debug view
        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(np.asanyarray(depth_frame.get_data()), alpha=0.03),
            cv2.COLORMAP_JET)
        cv2.imshow("Depth Map", depth_colormap)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows() 
#
import sys
import cv2
import numpy as np
import pyrealsense2 as rs
from yoloDet import YoloTRT

# Load YOLO-TensorRT model
model = YoloTRT(
    library="yolov5/buildM/libmyplugins.so",
    engine="yolov5/buildM/best.engine",
    conf=0.5,
    yolo_ver="v5"
)

# Enhanced depth estimator
def get_precise_depth(depth_frame, x1, y1, x2, y2, sample_ratio=0.2):
    w = x2 - x1
    h = y2 - y1
    dx = int(w * sample_ratio)
    dy = int(h * sample_ratio)

    x_start = max(x1 + dx, 0)
    x_end = min(x2 - dx, depth_frame.get_width())
    y_start = max(y1 + dy, 0)
    y_end = min(y2 - dy, depth_frame.get_height())

    depth_values = []
    for y in range(y_start, y_end, 2):  # sample every 2 pixels
        for x in range(x_start, x_end, 2):
            d = depth_frame.get_distance(x, y)
            if 0 < d < 5:
                depth_values.append(d)

    if not depth_values:
        return 0

    depth_array = np.array(depth_values)
    median = np.median(depth_array)
    filtered = depth_array[np.abs(depth_array - median) < 0.1]
    return np.mean(filtered) if filtered.size > 0 else median

# Initialize RealSense pipeline
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 60)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 60)
profile = pipeline.start(config)

# Set high accuracy preset
depth_sensor = profile.get_device().first_depth_sensor()
if depth_sensor.supports(rs.option.visual_preset):
    try:
        depth_sensor.set_option(rs.option.visual_preset, 2.0)  # High Accuracy
    except Exception as e:
        print(f"Failed to set visual preset: {e}")

# Enable auto exposure on color sensor
sensors = profile.get_device().query_sensors()
if len(sensors) > 1 and sensors[1].supports(rs.option.enable_auto_exposure):
    sensors[1].set_option(rs.option.enable_auto_exposure, 1)

# Align depth to color
align = rs.align(rs.stream.color)

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

        for det in detections:
            x1, y1, x2, y2 = map(int, det['box'])
            cls = det['class']
            conf = det['conf']
            label = f"{cls} {conf:.2f}"

            # Use improved depth estimation
            distance = get_precise_depth(depth_frame, x1, y1, x2, y2)

            if 0 < distance <= 5.0:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(frame, f"{distance:.2f} m", ((x1+x2)//2, (y1+y2)//2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Show FPS
        cv2.putText(frame, f"FPS: {1/t:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Show color and depth
        cv2.imshow("YOLOv5 + RealSense Distance", frame)
        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(np.asanyarray(depth_frame.get_data()), alpha=0.03),
            cv2.COLORMAP_JET)
        cv2.imshow("Depth Map", depth_colormap)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
#3
import cv2
import numpy as np
import pyrealsense2 as rs
from yoloDet import YoloTRT
import time

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

        # Display stream
        cv2.imshow("YOLOv5 + RealSense Stream", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
