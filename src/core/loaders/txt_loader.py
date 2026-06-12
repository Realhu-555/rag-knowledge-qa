"""纯文本文件加载器"""
from pathlib import Path

from src.core.loaders.base import BaseLoader, DocumentElement, ElementType


class TxtLoader(BaseLoader):
    """纯文本文件加载器，支持chardet自动检测编码"""

    def __init__(self):
        """初始化加载器"""
        try:
            import chardet  # noqa: F401
            self._chardet_available = True
        except ImportError:
            self._chardet_available = False

    @classmethod
    def can_handle(cls, file_path: Path) -> bool:
        """判断是否能处理该文件

        Args:
            file_path: 文件路径

        Returns:
            True表示可以处理
        """
        return file_path.suffix.lower() in ['.txt', '.text', '.log']

    def load(self, file_path: Path) -> list[DocumentElement]:
        """加载纯文本文件

        Args:
            file_path: 文本文件路径

        Returns:
            文档元素列表
        """
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        content = self._read_with_encoding(file_path)

        if not content.strip():
            return []

        return [DocumentElement(
            content=content,
            element_type=ElementType.TEXT,
            metadata={
                "file_type": "text",
                "encoding": self._detected_encoding,
            },
            source_file=str(file_path),
        )]

    def _read_with_encoding(self, file_path: Path) -> str:
        """读取文件并自动检测编码

        Args:
            file_path: 文件路径

        Returns:
            文件内容
        """
        raw_bytes = file_path.read_bytes()

        if self._chardet_available:
            import chardet
            result = chardet.detect(raw_bytes)
            self._detected_encoding = result['encoding'] or 'utf-8'
            confidence = result.get('confidence', 0)

            if confidence < 0.5:
                self._detected_encoding = 'utf-8'
        else:
            self._detected_encoding = 'utf-8'

        try:
            return raw_bytes.decode(self._detected_encoding)
        except (UnicodeDecodeError, LookupError):
            # 回退到utf-8
            self._detected_encoding = 'utf-8'
            return raw_bytes.decode('utf-8', errors='ignore')

    @classmethod
    def supported_extensions(cls) -> list[str]:
        """返回支持的文件扩展名"""
        return ['.txt', '.text', '.log']
