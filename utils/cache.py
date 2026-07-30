import time
import asyncio
from typing import Dict, Any, Optional

class AsyncTTLCache:
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self.cache: Dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self.cache:
                created_at, value = self.cache[key]
                if time.time() - created_at < self.ttl:
                    return value
                del self.cache[key]
            return None

    async def set(self, key: str, value: Any):
        async with self._lock:
            self.cache[key] = (time.time(), value)

# グローバルキャッシュ定義
search_cache = AsyncTTLCache(ttl=300)   # 5分
video_cache = AsyncTTLCache(ttl=1200)   # 20分
channel_cache = AsyncTTLCache(ttl=1800) # 30分
