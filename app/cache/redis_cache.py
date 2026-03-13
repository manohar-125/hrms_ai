import redis
import json
import re


class RedisCache:

    def __init__(self):
        try:
            self.client = redis.Redis(
                host="localhost",
                port=6379,
                decode_responses=True
            )
            self.client.ping()
            self.enabled = True
        except:
            print("Redis not available, cache disabled")
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
        except:
            pass