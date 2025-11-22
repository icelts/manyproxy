import json
import logging
import time
from collections import defaultdict
from typing import Any, Dict, Optional

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis客户端
redis_client = None
async def init_redis():
    global redis_client
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # 测试连接
        await redis_client.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Cache will be disabled.")
        redis_client = None


class CacheService:
    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """获取缓存"""
        if not redis_client:
            return None
        try:
            value = await redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    @staticmethod
    async def set(key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存"""
        if not redis_client:
            return False
        try:
            await redis_client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False
    
    @staticmethod
    async def delete(key: str) -> bool:
        """删除缓存"""
        if not redis_client:
            return False
        try:
            await redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False
    
    @staticmethod
    async def exists(key: str) -> bool:
        """检查键是否存在"""
        if not redis_client:
            return False
        try:
            return bool(await redis_client.exists(key))
        except Exception as e:
            logger.warning(f"Cache exists error: {e}")
            return False
    
    @staticmethod
    async def increment(key: str, amount: int = 1) -> int:
        """递增计数器"""
        if not redis_client:
            return 0
        try:
            return await redis_client.incrby(key, amount)
        except Exception as e:
            logger.warning(f"Cache increment error: {e}")
            return 0
    
    @staticmethod
    async def expire(key: str, ttl: int) -> bool:
        """设置过期时间"""
        if not redis_client:
            return False
        try:
            await redis_client.expire(key, ttl)
            return True
        except Exception as e:
            logger.warning(f"Cache expire error: {e}")
            return False


class RateLimiter:
    _memory_cache: Dict[str, Dict[int, int]] = defaultdict(dict)

    def __init__(self, max_requests: int = 1000, window: int = 60):
        self.max_requests = max_requests
        self.window = window
    
    async def is_allowed(self, identifier: str, max_requests: Optional[int] = None) -> bool:
        """检查是否允许请求"""
        limit = max_requests or self.max_requests
        if not redis_client:
            return self._is_allowed_memory(identifier, limit)
        
        current_time = int(time.time())
        key = f"rate_limit:{identifier}:{current_time // self.window}:{limit}"
        
        try:
            requests = await redis_client.incr(key)
            if requests == 1:
                await redis_client.expire(key, self.window)
            
            return requests <= limit
        except Exception as e:
            logger.warning(f"Rate limiter error: {e}, falling back to memory cache")
            return self._is_allowed_memory(identifier, limit)
    
    def _is_allowed_memory(self, identifier: str, limit: int) -> bool:
        """内存限流实现"""
        current_time = int(time.time())
        window_key = current_time // self.window
        memory_key = f"{identifier}:{limit}"
        bucket = self._memory_cache[memory_key]
        
        old_windows = [w for w in bucket.keys() if w < window_key]
        for old_window in old_windows:
            bucket.pop(old_window, None)
        
        bucket[window_key] = bucket.get(window_key, 0) + 1
        return bucket[window_key] <= limit


# 创建一个默认的限流器实例，避免Redis连接失败时的错误
default_rate_limiter = RateLimiter()
