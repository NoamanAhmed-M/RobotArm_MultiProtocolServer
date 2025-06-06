import sys
import cv2
import numpy as np
import pyrealsense2 as rs
from yoloDet import YoloTRT
from motor_control import move_forward_step, turn_left_step, turn_right_step, stop_all, cleanup

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

# Depth preset
depth_sensor = profile.get_device().first_depth_sensor()
if depth_sensor.supports(rs.option.visual_preset):
    try:
        depth_sensor.set_option(rs.option.visual_preset, 2.0)
    except Exception as e:
        print(f"[!] Preset Error: {e}")

# Auto exposure
sensors = profile.get_device().query_sensors()
if len(sensors) > 1 and sensors[1].supports(rs.option.enable_auto_exposure):
    sensors[1].set_option(rs.option.enable_auto_exposure, 1)

# Align depth to color
align = rs.align(rs.stream.color)

# === Depth Helper ===
def get_average_depth(depth_frame, cx, cy, k=7):
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
    filtered = [v for v in values if abs(v - median) < 0.3]
    return np.mean(filtered) if filtered else median

# === Main Loop ===
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

        h, w, _ = frame.shape
        center_x = w // 2

        for det in detections:
            x1, y1, x2, y2 = map(int, det['box'])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            distance = get_average_depth(depth_frame, cx, cy)

            # === Visualization ===
            label = f"{det['class']} {det['conf']:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(frame, f"{distance:.2f} m", (cx, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # === Navigation Logic (Stop at 40cm) ===
            offset = cx - center_x
            threshold = w // 10

            if distance > 0.4 and distance < 2.0:
                if offset < -threshold:
                    turn_left_step(30, 30, 0.1)
                elif offset > threshold:
                    turn_right_step(30, 30, 0.1)
                else:
                    move_forward_step(40, 38, 0.2)
            else:
                stop_all()

            break  # process only first detection

        # FPS info
        cv2.putText(frame, f"FPS: {1/t:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Display
        cv2.imshow("YOLO + RealSense", frame)
        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(np.asanyarray(depth_frame.get_data()), alpha=0.03),
            cv2.COLORMAP_JET)
        cv2.imshow("Depth Map", depth_colormap)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cleanup()
    cv2.destroyAllWindows()
    print("[✔] Shutdown complete.")
