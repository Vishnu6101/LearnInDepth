from fastapi import HTTPException
import redis

redis_client = redis.Redis(
    host="redis",  # localhost for local testing
    port=6379,
    decode_responses=True
)

# Check availability
def redis_alive() -> bool:
    try:
        redis_client.ping()
        return True
    except redis.RedisError:
        return False
    

def get_redis_connection():
    if not redis_alive():
        raise HTTPException(status_code=503, detail="Redis Unavailable")
    return redis_client