"""Loader统一接口"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DocumentElement:
    """标准化的文档元素"""
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseLoader(ABC):
    """文档加载器基类"""

    @abstractmethod
    def load(self, file_path: Path) -> list[DocumentElement]:
        """加载文档，返回标准化的文档元素列表"""
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名"""
        pass
