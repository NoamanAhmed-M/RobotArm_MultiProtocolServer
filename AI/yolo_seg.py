import sys
import cv2
import numpy as np
import pyrealsense2 as rs
from yoloDet import YoloTRT  # Ensure this handles segmentation output!

# Load YOLOv5 TensorRT segmentation model
model = YoloTRT(
    library="yolov5/buildM/libmyplugins.so",
    engine="yolov5/buildM/best.engine",
    conf=0.5,
    yolo_ver="v5seg"  # Just a flag; adjust according to how YoloTRT handles segmentation
)

# Helper: Calculate average depth of mask pixels
def get_mask_depth(depth_frame, mask, k=5):
    coords = np.argwhere(mask)
    if coords.size == 0:
        return 0
    depths = []
    for y, x in coords[::k]:  # Sample every kth pixel to speed up
        if 0 <= x < depth_frame.get_width() and 0 <= y < depth_frame.get_height():
            d = depth_frame.get_distance(x, y)
            if d > 0:
                depths.append(d)
    if not depths:
        return 0
    median = np.median(depths)
    filtered = [d for d in depths if abs(d - median) < 0.3]
    return np.mean(filtered) if filtered else median

# RealSense initialization
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 424, 240, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 30)
profile = pipeline.start(config)

# Set depth sensor preset to High Accuracy
depth_sensor = profile.get_device().first_depth_sensor()
if depth_sensor.supports(rs.option.visual_preset):
    try:
        depth_sensor.set_option(rs.option.visual_preset, 2.0)
        name = depth_sensor.get_option_value_description(rs.option.visual_preset, 2.0)
        print(f"Visual Preset set to: {name}")
    except Exception as e:
        print(f"Failed to set visual preset: {e}")

# Enable auto-exposure for color stream
sensors = profile.get_device().query_sensors()
if len(sensors) > 1 and sensors[1].supports(rs.option.enable_auto_exposure):
    sensors[1].set_option(rs.option.enable_auto_exposure, 1)

align = rs.align(rs.stream.color)

try:
    while True:
        frames = pipeline.wait_for_frames()
        aligned_frames = align.process(frames)

        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        color_image = np.asanyarray(color_frame.get_data())
        detections, t = model.Inference(color_image)

        for det in detections:
            x1, y1, x2, y2 = map(int, det['box'])
            label = f"{det['class']} {det['conf']:.2f}"

            # Get mask: assuming 'mask' is a binary mask of shape (H, W)
            mask = det.get('mask')
            if mask is None:
                continue

            # Resize mask to match frame size if needed
            mask_resized = cv2.resize(mask.astype(np.uint8) * 255, (color_image.shape[1], color_image.shape[0]))
            mask_binary = (mask_resized > 128).astype(np.uint8)

            # Apply mask to frame
            color_mask = np.zeros_like(color_image)
            color_mask[:, :, 1] = mask_binary * 255  # green mask
            segmented = cv2.addWeighted(color_image, 1.0, color_mask, 0.5, 0)

            # Estimate depth from mask
            distance = get_mask_depth(depth_frame, mask_binary)

            # Draw bounding box + info
            if 0 < distance <= 5.0:
                cv2.rectangle(segmented, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(segmented, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                cv2.putText(segmented, f"{distance:.2f} m", (cx, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            color_image = segmented

        # FPS
        cv2.putText(color_image, f"FPS: {1/t:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        cv2.imshow("YOLOv5 Segmentation + RealSense", color_image)

        # Optional: show raw depth
        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(np.asanyarray(depth_frame.get_data()), alpha=0.03),
            cv2.COLORMAP_JET)
        cv2.imshow("Depth Map", depth_colormap)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
