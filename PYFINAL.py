import asyncio
import websockets

@asyncio.coroutine
def connect_to_server():
    uri = "ws://<RASPBERRY_IP>:8765"

    try:
        websocket = yield from websockets.connect(uri)
        print("Connected to server!")

        while True:
            yield from websocket.send("Hello from Jetson!")
            response = yield from websocket.recv()
            print("Received from server:", response)
            yield from asyncio.sleep(1)

    except Exception as e:
        print("Connection failed:", e)

loop = asyncio.get_event_loop()
loop.run_until_complete(connect_to_server())
