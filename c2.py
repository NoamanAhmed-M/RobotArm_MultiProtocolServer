import cv2
import socket
import struct
import time
import sys

# Server configuration
SERVER_IP = '10.65.102.37'  # Make sure there's no leading space
SERVER_PORT = 5005
MAX_DGRAM = 65000  # Slightly below the max UDP size (65507)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"Connecting to {SERVER_IP}:{SERVER_PORT}")

# Open camera or video file
cap = cv2.VideoCapture(0)  # Use 'video.mp4' instead of 0 for a video file
if not cap.isOpened():
    print("Failed to open camera")
    sys.exit(1)

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
            
        # Resize the frame
        frame = cv2.resize(frame, (640, 480))
        
        # Add frame number overlay
        cv2.putText(frame, f"Frame: {frame_num}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Encode to JPEG
        _, encoded_img = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        img_data = encoded_img.tobytes()
        
        data_size = len(img_data)
        
        # Split the image data into chunks
        chunks = [img_data[i:i + MAX_DGRAM - 8] for i in range(0, len(img_data), MAX_DGRAM - 8)]
        total_chunks = len(chunks)
        
        if frame_num % 30 == 0:  # Log every 30 frames
            print(f"Sending frame {frame_num} (size: {data_size} bytes, chunks: {total_chunks})")
        
        for chunk in chunks:
            # Packet header: frame_num (4 bytes), total_chunks (4 bytes)
            header = struct.pack('>II', frame_num, total_chunks)
            sock.sendto(header + chunk, (SERVER_IP, SERVER_PORT))
        
        frame_num += 1
        frames_sent += 1
        
        # Calculate and display FPS
        now = time.time()
        if now - last_fps_time >= 5.0:
            fps = frames_sent / (now - last_fps_time)
            print(f"Sending at {fps:.2f} FPS")
            frames_sent = 0
            last_fps_time = now
        
        # Control frame rate
        time.sleep(1 / 30)  # Target 30 FPS

except KeyboardInterrupt:
    print("Stopped by user")
except Exception as e:
    print(f"Error: {e}")
finally:
    cap.release()
    sock.close()
    print("Connection closed")
