import cv2
import socket
import time
import struct
import sys

# Jetson IP and port (change to your Jetson's actual IP)
DEST_IP = '192.168.146.136'  # Jetson IP
DEST_PORT = 5005

# Setup UDP socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except socket.error as e:
    print(f"Socket creation error: {e}")
    sys.exit(1)

# Open USB camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open camera")
    sys.exit(1)

# Set camera properties - using numeric indices for compatibility
cap.set(3, 320)  # Width - using index 3 for compatibility
cap.set(4, 240)  # Height - using index 4 for compatibility

MAX_DGRAM = 65507  # Max UDP packet size

print("Starting video streaming to {}:{}".format(DEST_IP, DEST_PORT))

running = True
try:
    while running:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame - retrying")
            time.sleep(0.1)
            continue
        
        # Encode frame to JPEG with quality parameter (0-100)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]  # Lower quality = smaller size
        ret, buffer = cv2.imencode('.jpg', frame, encode_param)
        if not ret:
            print("Failed to encode frame")
            continue
            
        data = buffer.tobytes()
        size = len(data)
        
        # Print frame size occasionally
        current_time = time.time()
        if int(current_time) % 5 == 0 and current_time - int(current_time) < 0.1:
            print("Frame size: {} bytes".format(size))
        
        num_chunks = (size // MAX_DGRAM) + 1
        
        for i in range(num_chunks):
            start = i * MAX_DGRAM
            end = min(size, start + MAX_DGRAM)
            chunk = data[start:end]
            
            # Header format: (index, total)
            header = struct.pack("HH", i, num_chunks)
            try:
                sock.sendto(header + chunk, (DEST_IP, DEST_PORT))
            except socket.error as e:
                print("Socket sending error: {}".format(e))
                break
        
        time.sleep(0.05)  # 20 FPS limit (adjust if needed)

except KeyboardInterrupt:
    print("Stopping video stream")
    running = False
except Exception as e:
    print("Error: {}".format(e))
    running = False
finally:
    # Clean up
    cap.release()
    sock.close()
    print("Resources released")
