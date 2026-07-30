import time
from typing import Dict, Any, Optional

class SimpleTTLCache:
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self.cache: Dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            created_at, value = self.cache[key]
            if time.time() - created_at < self.ttl:
                return value
            del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        self.cache[key] = (time.time(), value)

search_cache = SimpleTTLCache(ttl=300)
video_cache = SimpleTTLCache(ttl=600)
