"""数据表定义"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DocumentRecord:
    """文档注册表记录"""
    id: str
    filename: str
    file_path: str
    file_hash: str
    file_type: str
    file_size: int
    chunk_count: int = 0
    status: str = "pending"  # pending/indexed/updating/deleted/error
    indexed_at: str = ""
    updated_at: str = ""
    error_message: str = ""

    @staticmethod
    def now() -> str:
        """返回当前时间的ISO格式字符串"""
        return datetime.now().isoformat(timespec="seconds")
