"""数据监控 WebSocket 广播器 — 推送文件变化和索引状态到前端"""
import asyncio
import json
import logging
import time
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class DataMonitorBroadcaster:
    """管理 data-monitor WebSocket 连接，广播文件变化事件"""

    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("数据监控连接建立，当前连接数: %d", len(self._connections))

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)
        logger.info("数据监控连接断开，当前连接数: %d", len(self._connections))

    async def broadcast(self, event_type: str, data: dict[str, Any]):
        """广播事件到所有连接的客户端"""
        message = json.dumps({
            "type": event_type,
            "timestamp": time.time(),
            **data,
        }, ensure_ascii=False)

        dead: list[WebSocket] = []
        async with self._lock:
            for ws in self._connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections.remove(ws)

    # ------------------------------------------------------------------
    # 便捷方法： watcher / indexer 调用
    # ------------------------------------------------------------------

    async def on_file_change(self, files: list[str], action: str = "detected"):
        """文件变化通知"""
        await self.broadcast("file_change", {
            "action": action,
            "files": files,
        })

    async def on_index_start(self, files: list[str]):
        """索引开始"""
        await self.broadcast("index_start", {
            "files": files,
            "count": len(files),
        })

    async def on_index_progress(self, current: int, total: int, filename: str = ""):
        """索引进度"""
        await self.broadcast("index_progress", {
            "current": current,
            "total": total,
            "filename": filename,
        })

    async def on_index_complete(self, stats: dict):
        """索引完成"""
        await self.broadcast("index_complete", {
            "stats": stats,
        })

    async def on_index_error(self, filename: str, error: str):
        """索引错误"""
        await self.broadcast("index_error", {
            "filename": filename,
            "error": error,
        })


# 全局单例
_monitor: DataMonitorBroadcaster | None = None


def get_data_monitor() -> DataMonitorBroadcaster:
    global _monitor
    if _monitor is None:
        _monitor = DataMonitorBroadcaster()
    return _monitor
