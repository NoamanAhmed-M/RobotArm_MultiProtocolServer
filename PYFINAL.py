import cv2
import base64
import asyncio
import websockets

async def send_video():
    uri = "ws://172.20.10.5:5005"
    cap = cv2.VideoCapture(0)

    async with websockets.connect(uri) as websocket:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

          
            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')

            await websocket.send(jpg_as_text)
            await asyncio.sleep(0.05) 

asyncio.run(send_video())
