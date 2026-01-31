import redis.asyncio as redis
import os
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), verbose=True)

REDIS_CONFIG = {
    "host": os.getenv("host"),
    "port": int(os.getenv("port")),
    "decode_responses": True,
    "username": "default",
    "password": os.getenv("password")
}
    # SSL is often required for cloud instances, set to True if you get connection errors
    # "ssl": True 


class RedisClient:
    def init(self):
        self.client = None

    async def connect(self):
        """Creates the Redis connection pool."""
        self.client = redis.Redis(**REDIS_CONFIG)
        # Test connection
        await self.client.ping()
        print("✅ Redis Connected")

    async def close(self):
        """Closes the Redis connection."""
        if self.client:
            await self.client.close()
            print("🔒 Redis Connection Closed")

    async def get_client(self) -> redis.Redis:
        """Dependency for routes to retrieve the client."""
        return self.client


redis_db = RedisClient()
