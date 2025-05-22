

import pyrealsense2 as rs
import numpy as np
import cv2

# Initialize RealSense
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

try:
    while True:
        # Wait for frames
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        # Convert to numpy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Convert to HSV color space
        hsv = cv2.cvtColor(color_image, cv2.COLOR_BGR2HSV)

        # Mask for white/light gray object (adjust these values if needed)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 40, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 300:  # Filter out small noise
                continue

            # Fit enclosing circle to contour
            (x, y), radius = cv2.minEnclosingCircle(cnt)
            x, y, r = int(x), int(y), int(radius)

            # Check circularity (optional)
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
            circularity = (4 * np.pi * area) / (perimeter ** 2)
            if 0.7 < circularity < 1.3:  # Circle-like
                # Get distance
                distance = depth_frame.get_distance(x, y)

                # Draw circle and distance
                cv2.circle(color_image, (x, y), r, (0, 255, 0), 2)
                cv2.circle(color_image, (x, y), 2, (0, 255, 0), 3)
                cv2.putText(color_image, f"{distance:.2f} m", (x - 40, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                break  # Only one target needed

        # Create colorized depth map
        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_image, alpha=0.03),
            cv2.COLORMAP_JET
        )

        # Combine both views side-by-side
        combined = np.hstack((color_image, depth_colormap))
        cv2.imshow("RealSense Object Detection", combined)

        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()

