import cv2
import socket
import struct
import time

# Server configuration
SERVER_IP = '10.65.102.37'  # Change to the actual server IP
SERVER_PORT = 5005
MAX_DGRAM = 60000  # Slightly below the max UDP size (65507)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Open camera or video file
cap = cv2.VideoCapture(0)  # Use 'video.mp4' instead of 0 for a video file
frame_num = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize the frame
        frame = cv2.resize(frame, (640, 480))
        _, encoded_img = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        img_data = encoded_img.tobytes()

        # Split the image data into chunks
        chunks = [img_data[i:i + MAX_DGRAM - 12] for i in range(0, len(img_data), MAX_DGRAM - 12)]
        total_chunks = len(chunks)

        for idx, chunk in enumerate(chunks):
            # Packet header: frame_num (4 bytes), total_chunks (4 bytes), chunk_index (4 bytes)
            header = struct.pack('>III', frame_num, total_chunks, idx)
            sock.sendto(header + chunk, (SERVER_IP, SERVER_PORT))

        frame_num += 1
        time.sleep(1 / 30)  # Approx. 30 FPS

except KeyboardInterrupt:
    print("Stopped by user")

finally:
    cap.release()
    sock.close()
