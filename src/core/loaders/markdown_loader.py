"""Markdown文档加载器"""
from pathlib import Path

from src.core.loaders.base import BaseLoader, DocumentElement, ElementType


class MarkdownLoader(BaseLoader):
    """Markdown文档加载器"""

    @classmethod
    def can_handle(cls, file_path: Path) -> bool:
        """判断是否能处理该文件

        Args:
            file_path: 文件路径

        Returns:
            True表示可以处理
        """
        return file_path.suffix.lower() in ['.md', '.markdown']

    def load(self, file_path: Path) -> list[DocumentElement]:
        """加载Markdown文件

        Args:
            file_path: Markdown文件路径

        Returns:
            文档元素列表
        """
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            return []

        return [DocumentElement(
            content=content,
            element_type=ElementType.TEXT,
            metadata={
                "file_type": "md",
            },
            source_file=str(file_path),
        )]

    @classmethod
    def supported_extensions(cls) -> list[str]:
        """返回支持的文件扩展名"""
        return ['.md', '.markdown']
