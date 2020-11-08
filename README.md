# Shoutout

## Realtime messaging with Redis PUB/SUB.

Shout-out is designed to work with [FastAPI websocket](https://fastapi.tiangolo.com/advanced/websockets/), while running behind [Gunicorn](https://gunicorn.org/) with multiple [Uvicorn workers](https://www.uvicorn.org/deployment/#gunicorn). Where a centralized caching layer (Redis) is required to maintain state (messages) across workers.

You can also use Shoutout as a standalone asynchronous application.

## Installation
```shell
pip install shoutout-py
```

## Usage

### Standalone

```python
import asyncio

from shoutout.broadcast import Broadcast

broadcast = Broadcast("redis://localhost:6379")


async def main():
    await broadcast.connect()
    async with broadcast.subscribe("hello") as subscriber:
        if subscriber:
            await broadcast.publish("hello", message={
                "channel": "hello", "message": "Hello World!"})
            async for _, msg in subscriber:
                print(msg)
                break


if __name__ == "__main__":
    asyncio.run(main())
```
_The example above is complete and should run as is._


### FastAPI

```python
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from shoutout.broadcast import Broadcast
from starlette.concurrency import run_until_first_complete

broadcast = Broadcast("redis://localhost:6379")
app = FastAPI(on_startup=[broadcast.connect], on_shutdown=[broadcast.disconnect])


async def ws_receiver(websocket):
    async for message in websocket.iter_text():
        await broadcast.publish(channel="shout", message={"msg": message})


async def ws_sender(websocket):
    async with broadcast.subscribe(channel="shout") as subscriber:
        if subscriber:
            async for _, msg in subscriber:
                await websocket.send_json(msg)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await run_until_first_complete(
        (ws_receiver, {"websocket": websocket}),
        (ws_sender, {"websocket": websocket}),
    )


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)
```
_The example above is complete and should run as is._

Run it:
```shell
uvicorn main:app --reload
```