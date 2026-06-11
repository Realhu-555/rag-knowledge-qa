"""Loader模块"""
from src.core.loaders.base import BaseLoader, DocumentElement, ElementType
from src.core.loaders.markdown_loader import MarkdownLoader
from src.core.loaders.docx_loader import DocxLoader
from src.core.loaders.pdf_loader import PdfLoader
from src.core.loaders.txt_loader import TxtLoader
from src.core.loaders.image_loader import ImageLoader

# 所有可用的loader列表
LOADERS = [MarkdownLoader, DocxLoader, PdfLoader, TxtLoader, ImageLoader]


def get_loader_for_file(file_path) -> BaseLoader | None:
    """根据文件路径获取合适的loader

    Args:
        file_path: 文件路径

    Returns:
        合适的loader实例，如果没有则返回None
    """
    from pathlib import Path

    path = Path(file_path) if not isinstance(file_path, Path) else file_path

    for loader_cls in LOADERS:
        if loader_cls.can_handle(path):
            return loader_cls()

    return None


__all__ = [
    "BaseLoader",
    "DocumentElement",
    "ElementType",
    "MarkdownLoader",
    "DocxLoader",
    "PdfLoader",
    "TxtLoader",
    "ImageLoader",
    "LOADERS",
    "get_loader_for_file",
]
