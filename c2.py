import cv2
import socket
import struct
import time
import sys
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Video Streamer for Jetson Nano')
    parser.add_argument('--ip', default='10.65.102.37', help='Server IP address')
    parser.add_argument('--port', type=int, default=5005, help='Server port')
    parser.add_argument('--fps', type=int, default=30, help='Target FPS')
    parser.add_argument('--width', type=int, default=640, help='Frame width')
    parser.add_argument('--height', type=int, default=480, help='Frame height')
    parser.add_argument('--quality', type=int, default=70, help='JPEG quality (1-100)')
    parser.add_argument('--camera', type=int, default=0, help='Camera index')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Server configuration
    SERVER_IP = args.ip
    SERVER_PORT = args.port
    MAX_DGRAM = 65000  # Max UDP packet size
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"Connecting to {SERVER_IP}:{SERVER_PORT}")

    # Open camera with GStreamer backend for better performance on Jetson
    pipeline = f"nvarguscamerasrc ! video/x-raw(memory:NVMM),width={args.width},height={args.height},format=NV12,framerate={args.fps}/1 ! nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! video/x-raw,format=BGR ! appsink"
    
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        # Fallback to regular camera if GStreamer fails
        print("GStreamer pipeline failed, falling back to regular camera")
        cap = cv2.VideoCapture(args.camera)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        cap.set(cv2.CAP_PROP_FPS, args.fps)
    
    if not cap.isOpened():
        print("Failed to open camera")
        sys.exit(1)

    print(f"Camera opened successfully at {args.width}x{args.height} @ {args.fps}FPS")

    frame_num = 0
    last_fps_time = time.time()
    frames_sent = 0
    frame_interval = 1.0 / args.fps

    try:
        while True:
            start_time = time.time()
            
            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame")
                break
                
            # Add frame number overlay (only every 10 frames to reduce overhead)
            if frame_num % 10 == 0:
                cv2.putText(frame, f"Frame: {frame_num}", (20, 30), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Encode to JPEG with hardware acceleration if available
            _, encoded_img = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), args.quality])
            img_data = encoded_img.tobytes()
            
            # Split the image data into chunks
            chunks = [img_data[i:i + MAX_DGRAM - 8] for i in range(0, len(img_data), MAX_DGRAM - 8)]
            total_chunks = len(chunks)
            
            for chunk in chunks:
                # Packet header: frame_num (4 bytes), total_chunks (4 bytes)
                header = struct.pack('>II', frame_num, total_chunks)
                sock.sendto(header + chunk, (SERVER_IP, SERVER_PORT))
            
            frame_num += 1
            frames_sent += 1
            
            # Calculate and display FPS
            now = time.time()
            if now - last_fps_time >= 2.0:
                fps = frames_sent / (now - last_fps_time)
                print(f"Sending at {fps:.2f} FPS (target: {args.fps})")
                frames_sent = 0
                last_fps_time = now
            
            # Maintain frame rate
            processing_time = time.time() - start_time
            sleep_time = max(0, frame_interval - processing_time)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("Stopped by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cap.release()
        sock.close()
        print("Resources released")

if __name__ == "__main__":
    main()
