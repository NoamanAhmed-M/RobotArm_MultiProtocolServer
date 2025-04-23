import cv2
import socket
import struct
import time
import sys

# Server configuration
SERVER_IP = '10.65.102.37'
SERVER_PORT = 5005
MAX_DGRAM = 65000  # Consider increasing if network supports larger packets

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"Connecting to {SERVER_IP}:{SERVER_PORT}")

# Open camera with higher FPS settings
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Failed to open camera")
    sys.exit(1)

# Try to set camera to higher FPS (not all cameras support this)
cap.set(cv2.CAP_PROP_FPS, 60)
# Set smaller resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Camera opened successfully")
frame_num = 0
last_fps_time = time.time()
frames_sent = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame")
            break
            
        # Skip resize since we set camera resolution directly
        # frame = cv2.resize(frame, (640, 480))
        
        # Optional: Only add overlay every N frames to reduce processing
        if frame_num % 5 == 0:
            cv2.putText(frame, f"Frame: {frame_num}", (20, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Lower quality for faster encoding
        _, encoded_img = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        img_data = encoded_img.tobytes()
        
        # Split and send
        chunks = [img_data[i:i + MAX_DGRAM - 8] for i in range(0, len(img_data), MAX_DGRAM - 8)]
        for chunk in chunks:
            header = struct.pack('>II', frame_num, len(chunks))
            sock.sendto(header + chunk, (SERVER_IP, SERVER_PORT))
        
        frame_num += 1
        frames_sent += 1
        
        # Reduce or remove sleep to maximize FPS
        # time.sleep(1 / 60)  # For 60 FPS target
        
        # Calculate FPS
        now = time.time()
        if now - last_fps_time >= 2.0:  # More frequent FPS updates
            fps = frames_sent / (now - last_fps_time)
            print(f"Sending at {fps:.2f} FPS")
            frames_sent = 0
            last_fps_time = now

except KeyboardInterrupt:
    print("Stopped by user")
finally:
    cap.release()
    sock.close()
