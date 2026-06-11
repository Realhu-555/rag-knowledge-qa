"""会话管理"""
import time
from dataclasses import dataclass, field

from src.config import MAX_HISTORY_ROUNDS, SESSION_TIMEOUT_MINUTES


@dataclass
class Message:
    """对话消息"""
    role: str  # user 或 assistant
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Session:
    """会话"""
    session_id: str
    messages: list[Message] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


class SessionManager:
    """会话管理器"""

    def __init__(self, timeout_minutes: int = SESSION_TIMEOUT_MINUTES):
        self.sessions: dict[str, Session] = {}
        self.timeout_seconds = timeout_minutes * 60
        self._last_cleanup = time.time()

    def get_or_create_session(self, session_id: str) -> Session:
        """获取或创建会话"""
        # 每5分钟自动清理一次过期会话
        if time.time() - self._last_cleanup > 300:
            self.cleanup_expired()
            self._last_cleanup = time.time()

        if session_id not in self.sessions:
            self.sessions[session_id] = Session(session_id=session_id)

        session = self.sessions[session_id]
        session.last_active = time.time()
        return session

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """添加消息到会话"""
        session = self.get_or_create_session(session_id)
        session.messages.append(Message(role=role, content=content))
        session.last_active = time.time()

        # 保留最近N轮对话（每轮2条消息：user + assistant）
        max_messages = MAX_HISTORY_ROUNDS * 2
        if len(session.messages) > max_messages:
            session.messages = session.messages[-max_messages:]

    def get_history(self, session_id: str) -> list[dict]:
        """获取对话历史"""
        session = self.get_or_create_session(session_id)
        return [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
        ]

    def cleanup_expired(self) -> None:
        """清理过期会话"""
        current_time = time.time()
        expired_ids = [
            sid for sid, session in self.sessions.items()
            if current_time - session.last_active > self.timeout_seconds
        ]
        for sid in expired_ids:
            del self.sessions[sid]
