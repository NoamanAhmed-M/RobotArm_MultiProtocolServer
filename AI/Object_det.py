import cv2
import mediapipe as mp
import pyrealsense2 as rs
import numpy as np

# Setup RealSense
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

# Setup MediaPipe object detector
mp_obj_det = mp.tasks.vision.ObjectDetector
BaseOptions = mp.tasks.BaseOptions
ObjectDetectorOptions = mp.tasks.vision.ObjectDetectorOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Load your model (TFLite)
options = ObjectDetectorOptions(
    base_options=BaseOptions(model_asset_path='your_model.tflite'),
    running_mode=VisionRunningMode.IMAGE
)
detector = mp_obj_det.create_from_options(options)

try:
    while True:
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        image = np.asanyarray(color_frame.get_data())

        # Convert to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)

        # Run detection
        result = detector.detect(mp_image)

        for detection in result.detections:
            bbox = detection.bounding_box
            x_center = int(bbox.origin_x + bbox.width / 2)
            y_center = int(bbox.origin_y + bbox.height / 2)

            distance = depth_frame.get_distance(x_center, y_center)
            cv2.rectangle(image, (bbox.origin_x, bbox.origin_y),
                          (bbox.origin_x + bbox.width, bbox.origin_y + bbox.height), (0, 255, 0), 2)
            cv2.putText(image, f"{distance:.2f} m", (bbox.origin_x, bbox.origin_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("MediaPipe + RealSense", image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
