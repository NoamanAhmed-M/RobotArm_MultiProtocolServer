import socket
import cv2
import numpy as np
import struct
import asyncio
import websockets
import base64

UDP_IP = "0.0.0.0"
UDP_PORT = 5005
MAX_DGRAM = 65507

connected_clients = set()
frame_queue = asyncio.Queue()
buffer_dict = {}

async def websocket_handler(websocket, path):
    print("[WS] Client connected.")
    connected_clients.add(websocket)
    try:
        while True:
            frame = await frame_queue.get()
            await websocket.send(frame)
    except websockets.exceptions.ConnectionClosed:
        print("[WS] Client disconnected.")
    finally:
        connected_clients.remove(websocket)

async def start_websocket_server():
    print(f"[WS] Starting WebSocket on ws://0.0.0.0:8765")
    server = await websockets.serve(websocket_handler, "0.0.0.0", 8765)
    return server

@asyncio.coroutine
def udp_receiver(loop):
    print(f"[UDP] Listening on {UDP_IP}:{UDP_PORT}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)

    while True:
        yield from asyncio.sleep(0)  # Let event loop breathe
        try:
            data, _ = sock.recvfrom(MAX_DGRAM)

            if len(data) < 4:
                continue

            index, total = struct.unpack("HH", data[:4])
            chunk = data[4:]

            if index == 0:
                buffer_dict.clear()

            buffer_dict[index] = chunk

            if len(buffer_dict) == total:
                full_data = b''.join(buffer_dict[i] for i in range(total))
                img_np = np.frombuffer(full_data, dtype=np.uint8)
                frame = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

                if frame is not None:
                    _, jpeg = cv2.imencode('.jpg', frame)
                    b64_data = base64.b64encode(jpeg.tobytes()).decode('utf-8')
                    yield from frame_queue.put(b64_data)
        except BlockingIOError:
            pass  # Just try again
        except Exception as e:
            print("UDP error:", e)

def main():
    loop = asyncio.get_event_loop()

    # Start both coroutines
    udp_task = loop.create_task(udp_receiver(loop))
    ws_server = loop.run_until_complete(start_websocket_server())

    try:
        print("[MAIN] Running event loop")
        loop.run_forever()
    except KeyboardInterrupt:
        print("[MAIN] Shutting down")
    finally:
        ws_server.close()
        loop.run_until_complete(ws_server.wait_closed())
        loop.close()

if __name__ == "__main__":
    main()
