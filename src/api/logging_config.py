"""结构化JSON日志配置 — M4生产监控"""
import json
import logging
import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# 当前请求的 request_id，由中间件设置
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class JSONFormatter(logging.Formatter):
    """将日志记录格式化为JSON"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "request_id": request_id_ctx.get("-"),
        }

        # 如果记录了额外字段（通过 extra 传入），合并进来
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(name: str = "rag", level: int = logging.INFO) -> logging.Logger:
    """配置JSON结构化日志"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    return logger


logger = setup_logger()


def log_request(method: str, path: str, status_code: int, latency_ms: float) -> None:
    """记录HTTP请求日志"""
    logger.info(
        f"{method} {path} {status_code}",
        extra={"extra_data": {
            "method": method,
            "path": path,
            "status_code": status_code,
            "latency_ms": round(latency_ms, 2),
        }},
    )


def log_llm_call(model: str, prompt_tokens: int, completion_tokens: int,
                 latency_ms: float) -> None:
    """记录LLM调用日志"""
    logger.info(
        f"LLM call: {model}",
        extra={"extra_data": {
            "event": "llm_call",
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": round(latency_ms, 2),
        }},
    )


def log_retrieval(query: str, top_k: int, results_count: int,
                  retrieval_ms: float) -> None:
    """记录检索日志"""
    logger.info(
        f"Retrieval: {results_count} results in {retrieval_ms:.1f}ms",
        extra={"extra_data": {
            "event": "retrieval",
            "query": query[:100],
            "top_k": top_k,
            "results_count": results_count,
            "retrieval_ms": round(retrieval_ms, 2),
        }},
    )
