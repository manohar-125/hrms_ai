import redis
import json
import re
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class RedisCache:

    def __init__(self):
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=True
            )
            self.client.ping()
            self.enabled = True
            logger.info("✓ Redis Cache ENABLED")
        except:
            logger.warning("✗ Redis Cache DISABLED - Using in-memory cache only")
            self.enabled = False

    def normalize_key(self, key: str):
        """
        Normalize query to avoid duplicate cache keys
        """
        key = key.lower()
        key = re.sub(r"\s+", " ", key).strip()
        return key

    def get(self, key):

        if not self.enabled:
            return None

        key = self.normalize_key(key)

        try:
            value = self.client.get(key)
            return json.loads(value) if value else None
        except:
            return None

    def set(self, key, value, ttl=600):

        if not self.enabled:
            return

        key = self.normalize_key(key)

        try:
            self.client.setex(key, ttl, json.dumps(value))
            logger.debug(f"Redis STORE: key cached with ttl={ttl}s")
        except:
            logger.warning(f"Redis set() error")


_DYNAMIC_VALUE_PATTERN = re.compile(
    r"\b(\d{1,6}|\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4})\b"
)


def normalize_query(query: str) -> str:
    """Normalize query for deterministic cache key generation."""
    text = (query or "").lower().strip()
    return re.sub(r"\s+", " ", text)


def should_skip_cache(query: str) -> bool:
    """Skip cache for short or dynamic queries."""
    normalized = normalize_query(query)
    if len(normalized.split()) < 3:
        return True
    return bool(_DYNAMIC_VALUE_PATTERN.search(normalized))


_cache = RedisCache()


def get_cache(key: str):
    """Read value from Redis cache with graceful fallback."""
    if not getattr(settings, "ENABLE_CACHE", True):
        return None
    return _cache.get(key)


def set_cache(key: str, value, ttl: int = 3600):
    """Write value to Redis cache with graceful fallback."""
    if not getattr(settings, "ENABLE_CACHE", True):
        return
    _cache.set(key, value, ttl=ttl)