import cv2
import numpy as np
import pyrealsense2 as rs
import time
from yoloDet import YoloTRT
from movement import (
    set_motor_direction_forward,
    set_motor_direction_backward,
    set_motor_direction_left,
    set_motor_direction_right,
    stop_all,
    cleanup
)

# === YOLO Detection Model Setup ===
model = YoloTRT(
    library="yolov5/buildM/libmyplugins.so",
    engine="yolov5/buildM/best.engine",
    conf=0.5,
    yolo_ver="v5"
)

# === Intel RealSense Camera Setup ===
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 424, 240, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 30)
profile = pipeline.start(config)
align = rs.align(rs.stream.color)

# === Helper Function to Get Average Depth Around a Point ===
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

# === Constants for Navigation Control ===
FRAME_CENTER_X = 424 // 2                # Half of the image width
CENTER_TOLERANCE = 40                    # Pixel range to consider object centered
TARGET_DISTANCE = 0.10                   # Stop distance in meters (10 cm)

# === Main Processing Loop ===
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

            # === Drawing Bounding Box and Depth Info ===
            label = f"{det['class']} {det['conf']:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(frame, f"{depth:.2f} m", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

            # === Navigation Logic ===
            if depth > TARGET_DISTANCE and depth < 2:
                # Determine direction based on object position
                if cx < FRAME_CENTER_X - CENTER_TOLERANCE:
                    set_motor_direction_left()
                elif cx > FRAME_CENTER_X + CENTER_TOLERANCE:
                    set_motor_direction_right()
                else:
                    set_motor_direction_forward()
                time.sleep(0.1)
                stop_all()
            else:
                stop_all()

        # === Display Window ===
        cv2.imshow("YOLOv5 + RealSense", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # === Cleanup GPIO and Close Resources ===
    pipeline.stop()
    cleanup()
    cv2.destroyAllWindows()
