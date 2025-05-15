import cv2
import socket
import struct
import time
import sys

def open_camera():
    for i in range(10):  # Retry for ~10 seconds
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("[Camera] Camera opened successfully")
            return cap
        else:
            print("[Camera] Waiting for camera to be connected...")
            cap.release()
            time.sleep(1)
    print("[Camera] Could not open camera after retries")
    sys.exit(1)

def start_udp_camera():
    SERVER_IP = '10.65.102.37'
    SERVER_PORT = 5005
    MAX_DGRAM = 1400  

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[Camera] Connecting to {SERVER_IP}:{SERVER_PORT}")

    cap = open_camera()
    frame_num = 0
    last_fps_time = time.time()
    frames_sent = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Camera] Lost connection to camera. Reconnecting...")
                cap.release()
                cap = open_camera()
                continue

            frame = cv2.resize(frame, (640, 480))
            cv2.putText(frame, f"Frame: {frame_num}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            _, encoded_img = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            img_data = encoded_img.tobytes()

            chunks = [img_data[i:i + MAX_DGRAM - 8] for i in range(0, len(img_data), MAX_DGRAM - 8)]
            total_chunks = len(chunks)

            if frame_num % 30 == 0:
                print(f"[Camera] Sending frame {frame_num} ({len(img_data)} bytes, {total_chunks} chunks)")

            for chunk in chunks:
                header = struct.pack('>II', frame_num, total_chunks)
                sock.sendto(header + chunk, (SERVER_IP, SERVER_PORT))

            frame_num += 1
            frames_sent += 1

            now = time.time()
            if now - last_fps_time >= 5.0:
                fps = frames_sent / (now - last_fps_time)
                print(f"[Camera] Sending at {fps:.2f} FPS")
                frames_sent = 0
                last_fps_time = now

            time.sleep(1 / 30)

    except KeyboardInterrupt:
        print("[Camera] Stopped by user")
    except Exception as e:
        print(f"[Camera] Error: {e}")
    finally:
        cap.release()
        sock.close()
        print("[Camera] Connection closed")
