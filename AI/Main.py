import torch
import cv2

# Load YOLOv5s model
model = torch.hub.load('ultralytics/yolov5', 'custom', path='yolov5s.pt', force_reload=False)

# Start camera
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera not accessible")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Resize for speed
    frame = cv2.resize(frame, (640, 480))

    # Detect with YOLO
    results = model(frame)

    # Draw results
    annotated = results.render()[0]

    # Show frame
    cv2.imshow("YOLOv5 - Jetson Nano", annotated)

    # Exit with ESC
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
