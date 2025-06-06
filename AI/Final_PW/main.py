# main.py - Smart step-based object tracking and movement
import cv2
import numpy as np
import pyrealsense2 as rs
import time
from yoloDet import YoloTRT
from movement import set_motor_direction_forward, stop_all, cleanup

# === YOLO Setup ===
model = YoloTRT(
    library="yolov5/buildM/libmyplugins.so",
    engine="yolov5/buildM/best.engine",
    conf=0.5,
    yolo_ver="v5"
)

# === RealSense Setup ===
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 424, 240, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 30)
profile = pipeline.start(config)
align = rs.align(rs.stream.color)

# === Helper ===
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

            # Visuals
            label = f"{det['class']} {det['conf']:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(frame, f"{depth:.2f} m", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

            # Move in steps only if object is far enough
            if depth > 0.4:
                set_motor_direction_forward()
                time.sleep(0.1)
                stop_all()

        cv2.imshow("YOLOv5 + RealSense", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cleanup()
    cv2.destroyAllWindows()
