"""Loader统一接口"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ElementType(Enum):
    """文档元素类型"""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    LIST = "list"
    CODE = "code"
    IMAGE_DESCRIPTION = "image_description"


@dataclass
class DocumentElement:
    """标准化的文档元素"""
    content: str
    element_type: ElementType = ElementType.TEXT
    metadata: dict[str, Any] = field(default_factory=dict)
    source_file: str = ""
    page_number: int | None = None


class BaseLoader(ABC):
    """文档加载器基类"""

    @classmethod
    @abstractmethod
    def can_handle(cls, file_path: Path) -> bool:
        """判断是否能处理该文件

        Args:
            file_path: 文件路径

        Returns:
            True表示可以处理
        """
        pass

    @abstractmethod
    def load(self, file_path: Path) -> list[DocumentElement]:
        """加载文档，返回标准化的文档元素列表"""
        pass

    @classmethod
    @abstractmethod
    def supported_extensions(cls) -> list[str]:
        """返回支持的文件扩展名"""
        pass
