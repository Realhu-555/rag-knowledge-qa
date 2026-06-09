"""限流中间件"""
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import RATE_LIMIT_DAILY, RATE_LIMIT_PER_MINUTE


class RateLimitMiddleware(BaseHTTPMiddleware):
    """API限流中间件"""

    def __init__(self, app):
        super().__init__(app)
        # 存储格式: {api_key: {"minute": [(timestamp, count)], "daily": count}}
        self.requests: dict[str, dict] = defaultdict(lambda: {
            "minute_timestamp": 0,
            "minute_count": 0,
            "daily_count": 0,
            "daily_date": ""
        })

    async def dispatch(self, request: Request, call_next: Callable):
        """检查限流"""
        # 从请求头获取API Key
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        api_key = auth_header[7:]
        if not api_key:
            return await call_next(request)

        # 获取当前时间
        current_time = time.time()
        current_minute = int(current_time // 60)
        current_date = time.strftime("%Y-%m-%d", time.localtime(current_time))

        # 获取或初始化记录
        record = self.requests[api_key]

        # 检查日期重置
        if record["daily_date"] != current_date:
            record["daily_count"] = 0
            record["daily_date"] = current_date

        # 检查分钟限流
        if record["minute_timestamp"] == current_minute:
            if record["minute_count"] >= RATE_LIMIT_PER_MINUTE:
                raise HTTPException(
                    status_code=429,
                    detail=f"每分钟请求次数超限（限制: {RATE_LIMIT_PER_MINUTE}次/分钟）"
                )
            record["minute_count"] += 1
        else:
            record["minute_timestamp"] = current_minute
            record["minute_count"] = 1

        # 检查每日限流
        if record["daily_count"] >= RATE_LIMIT_DAILY:
            raise HTTPException(
                status_code=429,
                detail=f"每日请求次数超限（限制: {RATE_LIMIT_DAILY}次/天）"
            )
        record["daily_count"] += 1

        return await call_next(request)
