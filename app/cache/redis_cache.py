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