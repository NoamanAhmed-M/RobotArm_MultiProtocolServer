import cv2
import socket
import time
import struct

# Jetson IP and port (change to your Jetson's actual IP)
DEST_IP = '192.168.146.136'  # Jetson IP
DEST_PORT = 5005

# Setup UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Open USB camera (change to '/dev/video0' if using CSI camera on Jetson Nano)
cap = cv2.VideoCapture(0)  # Use 0 for USB camera or "/dev/video0" for CSI camera
if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

# Set resolution (this may need adjustment based on your camera)
cap.set(3, 320)  # Width
cap.set(4, 240)  # Height

MAX_DGRAM = 65507  # Max UDP packet size

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame")
        continue

    # Encode frame to JPEG
    ret, buffer = cv2.imencode('.jpg', frame)
    if not ret:
        continue

    data = buffer.tobytes()
    size = len(data)
    num_chunks = (size // MAX_DGRAM) + 1

    for i in range(num_chunks):
        start = i * MAX_DGRAM
        end = min(size, start + MAX_DGRAM)
        chunk = data[start:end]

        # Header format: (index, total)
        header = struct.pack("HH", i, num_chunks)
        sock.sendto(header + chunk, (DEST_IP, DEST_PORT))

    time.sleep(0.05)  # 20 FPS limit (adjust if needed)
