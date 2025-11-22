import time
import uuid
from typing import Optional, Dict, Any, List, AsyncGenerator

from upstash_redis.asyncio import Redis as UpstashHttpRedis
from redis.asyncio import Redis as RedisAsyncio


class UnifiedRedisManager:
    """
    Unified manager:
    - Upstash HTTP client: KV, sets, hashes, streams
    - Redis asyncio client: Pub/Sub for real-time messages
    """

    def __init__(
        self,
        http_url: str,
        http_token: str,
        resp_host: str,
        resp_port: int,
        resp_password: str,
    ):
        # HTTP client
        self.http = UpstashHttpRedis(url=http_url, token=http_token)

        # RESP client for Pub/Sub
        self.resp = RedisAsyncio(
            host=resp_host,
            port=resp_port,
            password=resp_password,
            ssl=True,
            decode_responses=True,
        )
        self.pubsub = self.resp.pubsub()

    # -----------------------------
    # User Connections (HTTP)
    # -----------------------------
    async def add_connected_user(self, user_id: str, socket_id: str):
        await self.http.sadd("ws:users", user_id)
        await self.http.hset(
            f"ws:user:{user_id}",
            values={"socket_id": socket_id, "connected_at": str(time.time())},
        )
        await self.http.hset(
            f"ws:socket:{socket_id}",
            values={"user_id": user_id, "connected_at": str(time.time())},
        )

    async def remove_connected_user(self, user_id: str, socket_id: str):
        await self.http.srem("ws:users", user_id)
        await self.http.delete(f"ws:user:{user_id}")
        await self.http.delete(f"ws:socket:{socket_id}")

    async def get_connected_users(self) -> List[str]:
        return await self.http.smembers("ws:users") or []

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.http.hgetall(f"ws:user:{user_id}")

    async def get_socket_info(self, socket_id: str) -> Optional[Dict[str, Any]]:
        return await self.http.hgetall(f"ws:socket:{socket_id}")

    # -----------------------------
    # Pub/Sub (RESP)
    # -----------------------------
    async def subscribe(self, channel: str):
        """Subscribe to a channel."""
        await self.pubsub.subscribe(channel)

    async def publish(self, channel: str, message: str):
        """Publish a message."""
        await self.resp.publish(channel, message)

    async def listen(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Async generator to listen to messages."""
        async for msg in self.pubsub.listen():
            if msg["type"] == "message":
                yield msg

    # -----------------------------
    # Helpers
    # -----------------------------
    def generate_socket_id(self) -> str:
        return str(uuid.uuid4())
