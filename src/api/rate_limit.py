"""限流中间件 — SQLite持久化版"""
import sqlite3
import time
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import RATE_LIMIT_DAILY, RATE_LIMIT_PER_MINUTE, RATE_LIMIT_DB


class RateLimitMiddleware(BaseHTTPMiddleware):
    """API限流中间件（SQLite持久化）"""

    def __init__(self, app):
        super().__init__(app)
        self._db_path = RATE_LIMIT_DB
        self._init_db()

    def _init_db(self) -> None:
        """创建数据库和表，启用工时模式提升并发性能"""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    key         TEXT    NOT NULL,
                    count       INTEGER NOT NULL DEFAULT 0,
                    window_start REAL   NOT NULL,
                    PRIMARY KEY (key)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（每请求一个连接）"""
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _check_and_increment(
        self, api_key: str, window_key: str, limit: int, window_start: float
    ) -> None:
        """原子操作：检查是否超限并计数+1，超限则抛出HTTPException"""
        conn = self._get_connection()
        try:
            full_key = f"{api_key}:{window_key}"
            cursor = conn.execute(
                "SELECT count, window_start FROM rate_limits WHERE key = ?",
                (full_key,),
            )
            row = cursor.fetchone()

            if row is None:
                # 首次请求，插入记录
                conn.execute(
                    "INSERT INTO rate_limits (key, count, window_start) VALUES (?, 1, ?)",
                    (full_key, window_start),
                )
            elif row[1] != window_start:
                # 新窗口，重置计数
                conn.execute(
                    "UPDATE rate_limits SET count = 1, window_start = ? WHERE key = ?",
                    (window_start, full_key),
                )
            elif row[0] >= limit:
                # 超限
                raise HTTPException(
                    status_code=429,
                    detail=f"请求次数超限（限制: {limit}次）",
                )
            else:
                # 未超限，计数+1
                conn.execute(
                    "UPDATE rate_limits SET count = count + 1 WHERE key = ?",
                    (full_key,),
                )

            conn.commit()
        except HTTPException:
            raise
        finally:
            conn.close()

    def _cleanup_expired(self) -> None:
        """清理过期记录：每天凌晨或低峰期可调用"""
        minute_window = int(time.time() // 60)
        conn = self._get_connection()
        try:
            # 清理分钟级过期记录（非当前分钟的）
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            conn.execute(
                "DELETE FROM rate_limits WHERE key LIKE '%%:minute' AND window_start != ?",
                (minute_window,),
            )
            # 清理非今天的每日记录
            conn.execute(
                "DELETE FROM rate_limits WHERE key LIKE '%%:daily' AND window_start != ?",
                (today,),
            )
            conn.commit()
        finally:
            conn.close()

    async def dispatch(self, request: Request, call_next: Callable):
        """检查限流"""
        # 从请求头获取API Key
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        api_key = auth_header[7:]
        if not api_key:
            return await call_next(request)

        # 当前分钟窗口
        current_minute = int(time.time() // 60)
        # 当日窗口
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 检查分钟限流
        self._check_and_increment(api_key, "minute", RATE_LIMIT_PER_MINUTE, current_minute)

        # 检查每日限流
        self._check_and_increment(api_key, "daily", RATE_LIMIT_DAILY, current_date)

        # 偶尔清理过期记录（约1%概率）
        if int(time.time()) % 100 == 0:
            self._cleanup_expired()

        return await call_next(request)
