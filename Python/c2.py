import cv2
import socket
import time
import struct

# Jetson IP and port
DEST_IP = '192.168.146.136'  # Replace with your Jetson's IP
DEST_PORT = 5005

# Setup UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Open USB camera
cap = cv2.VideoCapture(0)
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
    num_chunks = int((size + MAX_DGRAM - 1) / MAX_DGRAM)  # Ensure rounding up

    for i in range(num_chunks):
        start = i * MAX_DGRAM
        end = min(size, start + MAX_DGRAM)
        chunk = data[start:end]

        # Header format: (index, total)
        header = struct.pack("HH", i, num_chunks)
        sock.sendto(header + chunk, (DEST_IP, DEST_PORT))

    time.sleep(0.05)  # Limit to 20 FPS
