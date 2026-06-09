"""日志配置"""
import logging
import sys


def setup_logger(name: str = "rag") -> logging.Logger:
    """配置日志"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logger()


def log_query(query: str, user_id: str = "anonymous"):
    """记录查询日志"""
    logger.info(f"Query from {user_id}: {query[:100]}...")


def log_response(query: str, response_time_ms: int, success: bool):
    """记录响应日志"""
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"Response [{status}] in {response_time_ms}ms")
