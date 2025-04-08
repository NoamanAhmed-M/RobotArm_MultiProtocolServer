import socket
import cv2
import numpy as np
import struct

# Setup
LISTEN_IP = '0.0.0.0'
PORT = 5005
MAX_DGRAM = 65507

# Create socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, PORT))
print(f"[INFO] Listening on UDP {LISTEN_IP}:{PORT}")

# Store received chunks
buffer_dict = {}

while True:
    packet, _ = sock.recvfrom(MAX_DGRAM)
    if len(packet) < 4:
        continue

    # Unpack the 4-byte header (index, total chunks)
    index, total = struct.unpack("HH", packet[:4])
    data = packet[4:]

    # If first chunk, reset buffer
    if index == 0:
        buffer_dict.clear()

    buffer_dict[index] = data

    # If all chunks are received
    if len(buffer_dict) == total:
        full_data = b''.join(buffer_dict[i] for i in range(total))

        try:
            img_np = np.frombuffer(full_data, dtype=np.uint8)
            frame = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

            if frame is not None:
                cv2.imshow('Camera Feed (UDP)', frame)
                if cv2.waitKey(1) == 27:  # ESC to quit
                    break
        except Exception as e:
            print("Decoding error:", e)

sock.close()
cv2.destroyAllWindows()
