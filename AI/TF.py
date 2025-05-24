import sys
import cv2 
import imutils
from yoloDet import YoloTRT

# تحميل النموذج المحول إلى TensorRT
model = YoloTRT(
    library="yolov5/build/libmyplugins.so",
    engine="yolov5/build/yolov5s.engine",
    conf=0.5,
    yolo_ver="v5"
)

# استخدام الكاميرا (0 = الكاميرا الافتراضية)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Error: Could not open camera.")
    sys.exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to grab frame.")
        break

    frame = imutils.resize(frame, width=600)
    detections, t = model.Inference(frame)

    # رسم نتائج الكشف
    for det in detections:
        x1, y1, x2, y2 = det['box']
        cls = det['class']
        conf = det['conf']
        label = f"{cls} {conf:.2f}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # عرض معدل الإطارات
    cv2.putText(frame, f"FPS: {1/t:.2f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    # عرض الإطار
    cv2.imshow("YOLOv5 + TensorRT - Live Camera", frame)

    key = cv2.waitKey(1)
    if key == ord('q'):
        break

# إنهاء التشغيل
cap.release()
cv2.destroyAllWindows()
