"""Markdown文档加载器"""
from pathlib import Path

from src.core.loaders.base import BaseLoader, DocumentElement


class MarkdownLoader(BaseLoader):
    """Markdown文档加载器"""

    def load(self, file_path: Path) -> list[DocumentElement]:
        """加载Markdown文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 基础元数据
        metadata = {
            "source": file_path.name,
            "file_type": "md",
            "file_path": str(file_path),
        }

        return [DocumentElement(content=content, metadata=metadata)]

    def supported_extensions(self) -> list[str]:
        return [".md"]
