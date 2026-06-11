"""调用链追踪 — M4生产监控

每次问答生成一个 trace_id，贯穿 查询理解 -> 检索 -> 重排 -> 生成。
trace 数据存 SQLite traces 表。
"""
import json
import sqlite3
import threading
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.config import BASE_DIR

# ---------------------------------------------------------------------------
# 上下文变量：当前 trace
# ---------------------------------------------------------------------------

current_trace_id: ContextVar[str] = ContextVar("trace_id", default="")

# ---------------------------------------------------------------------------
# 数据库
# ---------------------------------------------------------------------------

DB_PATH = BASE_DIR / "data" / "rag.db"
_db_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_traces_table() -> None:
    """建表（幂等）"""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                user_id TEXT DEFAULT '',
                status TEXT DEFAULT 'ok',
                stages TEXT DEFAULT '{}',
                total_ms REAL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Span：单个阶段的数据
# ---------------------------------------------------------------------------

@dataclass
class Span:
    """一个处理阶段的追踪数据"""
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    data: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        return round((self.end_time - self.start_time) * 1000, 2)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            **self.data,
        }


# ---------------------------------------------------------------------------
# Trace：一次完整问答的追踪
# ---------------------------------------------------------------------------

class Trace:
    """一次 RAG 问答的完整调用链"""

    def __init__(self, query: str, user_id: str = ""):
        self.trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        self.query = query
        self.user_id = user_id
        self.status = "ok"
        self.spans: list[Span] = []
        self._current_span: Span | None = None
        self.start_time = time.time()

    # ---- span 管理 ----

    def start_span(self, name: str) -> Span:
        """开始一个阶段"""
        span = Span(name=name, start_time=time.time())
        self._current_span = span
        return span

    def end_span(self, data: dict | None = None) -> None:
        """结束当前阶段"""
        if self._current_span is not None:
            self._current_span.end_time = time.time()
            if data:
                self._current_span.data.update(data)
            self.spans.append(self._current_span)
            self._current_span = None

    # ---- 持久化 ----

    def finish(self) -> None:
        """结束追踪并写入 SQLite"""
        total_ms = round((time.time() - self.start_time) * 1000, 2)
        stages = {s.name: s.to_dict() for s in self.spans}
        now = datetime.now(timezone.utc).isoformat()

        with _db_lock:
            conn = _get_conn()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO traces "
                    "(id, query, user_id, status, stages, total_ms, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (self.trace_id, self.query[:500], self.user_id,
                     self.status, json.dumps(stages, ensure_ascii=False),
                     total_ms, now),
                )
                conn.commit()
            finally:
                conn.close()


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def get_trace(trace_id: str) -> dict | None:
    """从 SQLite 读取一条 trace"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM traces WHERE id = ?", (trace_id,)
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["stages"] = json.loads(result["stages"]) if result["stages"] else {}
        return result
    finally:
        conn.close()


def list_recent_traces(limit: int = 20) -> list[dict]:
    """列出最近的 trace"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT id, query, user_id, status, total_ms, created_at "
            "FROM traces ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
