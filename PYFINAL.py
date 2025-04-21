import asyncio
import websockets
import cv2
import base64

@asyncio.coroutine
def connect_to_server():
    uri = "ws://<RASPBERRY_IP>:8765"  # Replace <RASPBERRY_IP> with the real IP
    cap = cv2.VideoCapture(0)  # Open default camera

    try:
        websocket = yield from websockets.connect(uri)
        print("Connected to server!")

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')

            yield from websocket.send(jpg_as_text)
            yield from asyncio.sleep(0.05)  # 20 FPS approx

    except Exception as e:
        print("Connection failed:", e)
    finally:
        cap.release()

# Run the coroutine
loop = asyncio.get_event_loop()
loop.run_until_complete(connect_to_server())
