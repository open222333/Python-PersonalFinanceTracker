import redis
from src import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB

_client = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD or None,
            db=REDIS_DB,
            decode_responses=True
        )
    return _client
