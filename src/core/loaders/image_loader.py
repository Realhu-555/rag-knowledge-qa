"""图片加载器"""
from pathlib import Path

from src.core.loaders.base import BaseLoader, DocumentElement, ElementType


class ImageLoader(BaseLoader):
    """图片加载器，使用OCR提取文本"""

    def __init__(self):
        """初始化加载器"""
        self._tesseract_available = False
        try:
            import pytesseract
            self._tesseract_available = True
        except ImportError:
            pass

    @classmethod
    def can_handle(cls, file_path: Path) -> bool:
        """判断是否能处理该文件

        Args:
            file_path: 文件路径

        Returns:
            True表示可以处理
        """
        return file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']

    def load(self, file_path: Path) -> list[DocumentElement]:
        """加载图片文件并进行OCR

        Args:
            file_path: 图片文件路径

        Returns:
            文档元素列表
        """
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        elements = []

        if self._tesseract_available:
            ocr_text = self._ocr_with_tesseract(file_path)
            if ocr_text and ocr_text.strip():
                elements.append(DocumentElement(
                    content=ocr_text.strip(),
                    element_type=ElementType.IMAGE_DESCRIPTION,
                    metadata={
                        "ocr_engine": "tesseract",
                        "element": "ocr_text",
                    },
                    source_file=str(file_path),
                ))

        # 如果OCR没有结果或不可用，添加占位描述
        if not elements:
            elements.append(DocumentElement(
                content=f"[图片: {file_path.name}]",
                element_type=ElementType.IMAGE_DESCRIPTION,
                metadata={
                    "ocr_engine": "none",
                    "element": "placeholder",
                },
                source_file=str(file_path),
            ))

        return elements

    def _ocr_with_tesseract(self, file_path: Path) -> str:
        """使用Tesseract进行OCR

        Args:
            file_path: 图片文件路径

        Returns:
            OCR提取的文本
        """
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(file_path)
            # 使用中文+英文识别
            text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            return text
        except Exception as e:
            print(f"OCR失败 {file_path}: {e}")
            return ""

    @classmethod
    def supported_extensions(cls) -> list[str]:
        """返回支持的文件扩展名"""
        return ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
