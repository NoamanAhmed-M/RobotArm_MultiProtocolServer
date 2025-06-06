# realsense_processing.py
import numpy as np
import pyrealsense2 as rs

pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 424, 240, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 30)
profile = pipeline.start(config)
align = rs.align(rs.stream.color)

def get_aligned_frames():
    frames = pipeline.wait_for_frames()
    aligned = align.process(frames)
    depth_frame = aligned.get_depth_frame()
    color_frame = aligned.get_color_frame()
    return depth_frame, color_frame

def stop_pipeline():
    pipeline.stop()

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
