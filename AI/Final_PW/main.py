Skip to content
Chat history

You said:
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



let's add to this code the following once it detects the item it use the following code # movement.py (revised: binary HIGH/LOW movement control)
import Jetson.GPIO as GPIO
import time

# === Pin Definitions ===
IN1 = 7
IN2 = 11
ENA = 13
IN3 = 27
IN4 = 16
ENB = 18

# === GPIO Setup ===
GPIO.setmode(GPIO.BCM)
for pin in [IN1, IN2, ENA, IN3, IN4, ENB]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# === Binary Movement Control ===
def set_motor_direction_forward():
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    GPIO.output(ENA, GPIO.HIGH)
    GPIO.output(ENB, GPIO.HIGH)

def set_motor_direction_backward():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    GPIO.output(ENA, GPIO.HIGH)
    GPIO.output(ENB, GPIO.HIGH)

def set_motor_direction_left():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    GPIO.output(ENA, GPIO.HIGH)
    GPIO.output(ENB, GPIO.HIGH)

def set_motor_direction_right():
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    GPIO.output(ENA, GPIO.HIGH)
    GPIO.output(ENB, GPIO.HIGH)

def stop_all():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    GPIO.output(ENA, GPIO.LOW)
    GPIO.output(ENB, GPIO.LOW)

def cleanup():
    stop_all()
    GPIO.cleanup()

to move towrords the object (the center of the bounding box) till the destance betweed them became 10 cm 
ChatGPT said:
لتحقيق طلبك — أي جعل العربة تتحرك نحو الكائن المكتشف باستخدام YOLO و RealSense حتى تصبح المسافة بينهما 10 سم — سنقوم بالتعديل على الكود كما يلي:

نضيف شرط التتبع عندما تكون المسافة أكبر من 0.1 متر.

نضيف منطق تحديد اتجاه الكائن بناءً على موقعه في إطار الصورة (يمين، يسار، أم في المنتصف).

نستخدم الحركات: للأمام، يمين، يسار.

نوقف العربة عندما تصل إلى 10 سم أو أقرب.

✅ الكود المعدّل: main.py
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

# === Constants ===
FRAME_CENTER_X = 424 // 2
CENTER_TOLERANCE = 40  # pixels
TARGET_DISTANCE = 0.10  # meters

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

            # Movement logic
            if depth > TARGET_DISTANCE and depth < 2:
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

        cv2.imshow("YOLOv5 + RealSense", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cleanup()
    cv2.destroyAllWindows()
✅ ملاحظات مهمة:
TARGET_DISTANCE هو الحد الذي تُوقف فيه العربة عند الاقتراب من الكائن (10 سم = 0.1 متر).

الكود يتحقق من تموضع مركز الكائن نسبةً إلى منتصف الشاشة ويقرر الاتجاه المناسب.

time.sleep(0.1) يضمن أن العربة تتحرك خطوة صغيرة وتعيد التحقق.

هل ترغب أيضًا بإضافة منطق لتفادي العقبات أثناء الحركة أو حفظ إحداثيات الكائن؟




No file chosenNo file chosen
ChatGPT can make mistakes. Check important info. See Cookie Preferences.
