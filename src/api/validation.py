"""输入验证"""
import re
from fastapi import HTTPException


BLOCKED_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"system\s+prompt",
]

MAX_QUERY_LENGTH = 2000
MAX_SESSION_ID_LENGTH = 100


def validate_query(query: str) -> str:
    """验证并清洗用户查询"""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="查询不能为空")

    query = query.strip()

    if len(query) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"查询长度不能超过{MAX_QUERY_LENGTH}字符"
        )

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            raise HTTPException(status_code=400, detail="查询包含不允许的内容")

    return query


def validate_session_id(session_id: str | None) -> str | None:
    """验证会话ID"""
    if session_id is None:
        return None

    session_id = session_id.strip()

    if len(session_id) > MAX_SESSION_ID_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"会话ID长度不能超过{MAX_SESSION_ID_LENGTH}字符"
        )

    if not re.match(r'^[a-zA-Z0-9\-_]+$', session_id):
        raise HTTPException(status_code=400, detail="会话ID格式无效")

    return session_id


def sanitize_output(text: str) -> str:
    """清洗输出内容"""
    return text
