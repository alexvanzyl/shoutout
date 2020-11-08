import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import aioredis
from aioredis.pubsub import Receiver

logger = logging.getLogger("shoutout.broadcaster")


class Broadcast:
    def __init__(self, connection_url: str) -> None:
        self.connection_url = connection_url
        self._pub_conn: Optional[aioredis.Redis] = None
        self._sub_conn: Optional[aioredis.Redis] = None
        self._receiver: Optional[Receiver] = None

    async def connect(
        self, *, conn_retries: int = 5, conn_retry_delay: int = 1, retry: int = 0
    ) -> "Broadcast":
        try:
            self._pub_conn = await aioredis.create_redis(self.connection_url)
            self._sub_conn = await aioredis.create_redis(self.connection_url)
            self._receiver = Receiver()
        except (ConnectionError, aioredis.RedisError, asyncio.TimeoutError) as e:
            if retry < conn_retries:
                logger.warning(
                    "Redis connection error %s %s %s, %d retries remaining...",
                    self.connection_url,
                    e.__class__.__name__,
                    e,
                    conn_retries - retry,
                )
                await asyncio.sleep(conn_retry_delay)
            else:
                logger.error("Connecting to Redis failed")
                raise
        else:
            if retry > 0:
                logger.info("Redis connection successful")
            return self

        return await self.connect(
            conn_retries=conn_retries,
            conn_retry_delay=conn_retry_delay,
            retry=retry + 1,
        )

    async def publish(
        self, channel: str, message: dict, retry_count: Optional[int] = None
    ) -> None:
        if self.has_pub_conn():
            await self._pub_conn.publish_json(channel=channel, obj=message)
        elif not self.has_pub_conn() and retry_count:
            try:
                await self.connect(conn_retries=retry_count)
            except ConnectionRefusedError:
                logger.warning(
                    f"Retry failed - cannot publish message to channel {channel}"
                )
                return None
        else:
            return None

    async def unsubscribe(self, channel: str) -> None:
        if self.has_sub_conn():
            await self._sub_conn.unsubscribe(channel)

    async def disconnect(self) -> None:
        self._pub_conn.close()
        self._sub_conn.close()

        await self._pub_conn.wait_closed()
        await self._sub_conn.wait_closed()

    @asynccontextmanager
    async def subscribe(
        self, channel: str, retry_count: Optional[int] = None
    ) -> AsyncIterator:
        if not self.has_sub_conn():
            if retry_count:
                try:
                    await self.connect(conn_retries=1)
                except ConnectionRefusedError:
                    logger.warning(
                        f"Retry failed; cannot subscribe to channel {channel}."
                    )
                    yield None
                    return
            else:
                yield None
                return

        await self._sub_conn.subscribe(self._receiver.channel(channel))

        yield self._receiver.iter(encoding="utf8", decoder=json.loads)

        await self.unsubscribe(channel)

    def has_sub_conn(self) -> bool:
        return not (self._sub_conn is None or self._sub_conn.closed)

    def has_pub_conn(self) -> bool:
        return not (self._pub_conn is None or self._pub_conn.closed)
