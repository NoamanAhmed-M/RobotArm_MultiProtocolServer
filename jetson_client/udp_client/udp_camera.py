import cv2
import socket
import struct
import time
import sys

def open_camera():
    while True:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("[Camera] Camera opened successfully")
            return cap
        else:
            print("[Camera] Waiting for camera... Make sure it is connected.")
            cap.release()
            time.sleep(1)

def start_udp_camera():
    SERVER_IP = '10.65.102.37'
    SERVER_PORT = 5005
    MAX_DGRAM = 65000

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
                print("[Camera] Frame read failed. Reconnecting camera...")
                cap.release()
                cap = open_camera()
                continue

            frame = cv2.resize(frame, (640, 480))
            cv2.putText(frame, f"Frame: {frame_num}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Encode frame
            success, encoded_img = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if not success:
                print("[Camera] Failed to encode frame")
                continue

            img_data = encoded_img.tobytes()
            chunks = [img_data[i:i + MAX_DGRAM - 8] for i in range(0, len(img_data), MAX_DGRAM - 8)]
            total_chunks = len(chunks)

            if frame_num % 30 == 0:
                print(f"[Camera] Sending frame {frame_num} ({len(img_data)} bytes, {total_chunks} chunks)")

            for chunk in chunks:
                header = struct.pack('>II', frame_num, total_chunks)
                try:
                    sock.sendto(header + chunk, (SERVER_IP, SERVER_PORT))
                except Exception as e:
                    print(f"[Camera] Failed to send chunk: {e}")
                    break  # Optionally retry send if needed

            frame_num += 1
            frames_sent += 1

            # Show FPS every 5 seconds
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
