"""查询结果LRU缓存"""
import hashlib
from cachetools import TTLCache


class QueryCache:
    """基于 cachetools 的 LRU 缓存，存储检索结果。

    - 最多缓存 1000 条
    - 每条 1 小时后自动过期
    """

    _DEFAULT_MAX = 1000
    _DEFAULT_TTL = 3600  # 1小时

    def __init__(self, maxsize: int = _DEFAULT_MAX, ttl: int = _DEFAULT_TTL):
        self.cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

    @staticmethod
    def _make_key(query: str, top_k: int) -> str:
        """用查询文本 + top_k 生成缓存 key"""
        raw = f"{query}|||{top_k}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, query: str, top_k: int) -> list[dict] | None:
        """查询缓存，命中返回序列化结果列表，未命中返回 None"""
        key = self._make_key(query, top_k)
        return self.cache.get(key)

    def set(self, query: str, top_k: int, results: list[dict]) -> None:
        """写入缓存"""
        key = self._make_key(query, top_k)
        self.cache[key] = results

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()

    @property
    def size(self) -> int:
        """当前缓存条目数"""
        return len(self.cache)
