import cv2
import socket
import time
import struct
import sys
import os

# Jetson IP and port (change to your Jetson's actual IP)
DEST_IP = '172.20.10.5'  # Jetson IP - verify this is correct
DEST_PORT = 5005

# Check network connectivity first
def check_network():
    response = os.system("ping -c 1 -W 2 " + DEST_IP + " > /dev/null 2>&1")
    if response != 0:
        print("WARNING: Cannot reach destination IP: {}".format(DEST_IP))
        print("Please check that the IP address is correct and the device is on the same network")
        print("Continuing anyway - will keep trying to send frames...")
        return False
    return True

# Setup UDP socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set socket timeout to prevent blocking indefinitely
    sock.settimeout(1.0)
except socket.error as e:
    print("Socket creation error: {}".format(e))
    sys.exit(1)

# Open USB camera
print("Opening camera...")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open camera")
    sys.exit(1)

# Set camera properties - using numeric indices for compatibility
cap.set(3, 320)  # Width - using index 3 for compatibility
cap.set(4, 240)  # Height - using index 4 for compatibility

MAX_DGRAM = 65507  # Max UDP packet size

# Check network before starting
check_network()

print("Starting video streaming to {}:{}".format(DEST_IP, DEST_PORT))
print("Press Ctrl+C to stop")

frame_count = 0
network_error_count = 0
last_network_check = time.time()

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
        frame_count += 1
        if frame_count % 100 == 0:  # Print every 100 frames
            print("Frame #{}: size = {} bytes".format(frame_count, size))
        
        # Periodically check network
        if current_time - last_network_check > 30:  # Every 30 seconds
            check_network()
            last_network_check = current_time
            network_error_count = 0  # Reset error counter after check
        
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
                network_error_count += 1
                if network_error_count < 5 or network_error_count % 100 == 0:
                    print("Network error: {}".format(e))
                    if network_error_count == 5:
                        print("Suppressing further network errors...")
                time.sleep(0.1)  # Short delay after an error
        
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
