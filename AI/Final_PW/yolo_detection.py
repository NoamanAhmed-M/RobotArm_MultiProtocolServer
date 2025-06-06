# yolo_detection.py
import cv2
from yoloDet import YoloTRT

model = YoloTRT(
    library="yolov5/buildM/libmyplugins.so",
    engine="yolov5/buildM/best.engine",
    conf=0.5,
    yolo_ver="v5"
)

def detect_objects(frame):
    detections, _ = model.Inference(frame)
    return detections
