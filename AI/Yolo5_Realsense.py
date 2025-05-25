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

# Helper function to average depth over a region
def get_average_depth(depth_frame, cx, cy, k=5):
    """
    Average depth over a k×k square around (cx, cy)
    """
    depth_values = []
    for dx in range(-k//2, k//2 + 1):
        for dy in range(-k//2, k//2 + 1):
            x = cx + dx
            y = cy + dy
            if 0 <= x < depth_frame.get_width() and 0 <= y < depth_frame.get_height():
                d = depth_frame.get_distance(x, y)
                if d > 0:
                    depth_values.append(d)
    return np.mean(depth_values) if depth_values else 0

# Initialize RealSense pipeline
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 424, 240, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 30)

# Start streaming
profile = pipeline.start(config)

# Align depth to color
align_to = rs.stream.color
align = rs.align(align_to)

try:
    while True:
        # Wait for frames and align them
        frames = pipeline.wait_for_frames()
        aligned_frames = align.process(frames)

        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        # Convert color frame to numpy array
        frame = np.asanyarray(color_frame.get_data())

        # Run inference
        detections, t = model.Inference(frame)

        for det in detections:
            x1, y1, x2, y2 = map(int, det['box'])
            cls = det['class']
            conf = det['conf']
            label = f"{cls} {conf:.2f}"

            # Center of the bounding box
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # Average depth near the center point
            distance = get_average_depth(depth_frame, cx, cy, k=5)

            # Only show objects within 5 meters
            if 0 < distance <= 5.0:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(frame, f"{distance:.2f} m", (cx, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Show FPS
        cv2.putText(frame, f"FPS: {1/t:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Show the result
        cv2.imshow("YOLOv5 + RealSense Distance", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
