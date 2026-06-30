import redis.asyncio as redis
from app.core.config import settings

# Initialize Redis connection pool
redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=settings.REDIS_DB,
    decode_responses=True
)

async def get_redis_client() -> redis.Redis:
    """
    Dependency or utility function to yield an async Redis client.
    """
    return redis.Redis(connection_pool=redis_pool)
