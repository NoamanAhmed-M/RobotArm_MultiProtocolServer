import pyrealsense2 as rs
import numpy as np
import cv2

# Initialize RealSense pipeline
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

try:
    while True:
        # Get frames
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        # Convert to numpy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Convert to grayscale and blur
        gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        # Detect circles
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=50,
            param1=50,
            param2=30,
            minRadius=10,
            maxRadius=60
        )

        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                # Draw the detected circle
                cv2.circle(color_image, (x, y), r, (0, 255, 0), 2)
                cv2.circle(color_image, (x, y), 2, (0, 0, 255), 3)

                # Measure the distance at the center of the circle
                distance = depth_frame.get_distance(x, y)

                # Show distance text
                cv2.putText(
                    color_image,
                    f"Distance: {distance:.2f} m",
                    (x - 50, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )

                break  # Only use the first circle

        # Create a color-mapped version of the depth image
        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_image, alpha=0.03),
            cv2.COLORMAP_JET
        )

        # Combine images side-by-side
        combined = np.hstack((color_image, depth_colormap))

        # Display
        cv2.imshow("RealSense - Object Detection & Distance", combined)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
