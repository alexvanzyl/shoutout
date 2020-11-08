import pytest
from shoutout import Broadcast


@pytest.mark.asyncio
async def test_pubsub_to_channel():
    b = Broadcast("redis://localhost:6379")
    await b.connect()

    async with b.subscribe("shout") as subscriber:
        assert subscriber
        message_to_send = {"channel": "shout", "message": "Hello World"}
        await b.publish("shout", message=message_to_send)
        async for _, msg in subscriber:
            assert msg["channel"] == message_to_send["channel"]
            assert msg["message"] == message_to_send["message"]

            await b.unsubscribe("shout")
            await b.disconnect()
