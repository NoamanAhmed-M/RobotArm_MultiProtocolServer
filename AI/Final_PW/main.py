# main.py (micro-step movement logic: 0.5s forward, then re-detect)
import cv2
import numpy as np
from yolo_detection import detect_objects
from realsense_processing import get_aligned_frames, stop_pipeline, get_center_depth
from movement import set_motor_direction_forward, stop_all, cleanup
import time

try:
    while True:
        depth_frame, color_frame = get_aligned_frames()
        if not depth_frame or not color_frame:
            continue

        frame = np.asanyarray(color_frame.get_data())
        detections = detect_objects(frame)

        if detections:
            det = detections[0]
            x1, y1, x2, y2 = map(int, det['box'])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            depth = get_center_depth(depth_frame, cx, cy)

            label = f"{det['class']} {det['conf']:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(frame, f"{depth:.2f} m", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

            if 0.3 < depth < 2.0:
                print(f"Short move toward object at {depth:.2f} m")
                set_motor_direction_forward()
                time.sleep(0.5)  # move forward for 0.5 seconds only
                stop_all()

        cv2.imshow("YOLO Live Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    stop_pipeline()
    cv2.destroyAllWindows()
    cleanup()
