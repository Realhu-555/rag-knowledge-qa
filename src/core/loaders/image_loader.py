"""图片加载器：OCR + LLM描述 + 图表分析"""
from pathlib import Path

from src.config import (
    OCR_LANGUAGES,
    IMAGE_LLM_DESCRIPTION,
    CHART_ANALYSIS_ENABLED,
)
from src.core.loaders.base import BaseLoader, DocumentElement, ElementType
from src.core.preprocessor import (
    generate_image_description,
)


class ImageLoader(BaseLoader):
    """图片加载器

    支持三种处理模式（按开关控制）：
    1. OCR提取文字（pytesseract，支持多语言）
    2. LLM生成图片描述（需要IMAGE_LLM_DESCRIPTION=true）
    3. 图表分析（需要CHART_ANALYSIS_ENABLED=true）
    """

    def __init__(self):
        """初始化加载器"""
        self._tesseract_available = False
        try:
            import pytesseract  # noqa: F401
            self._tesseract_available = True
        except ImportError:
            pass

        self._chart_analyzer = None

    @classmethod
    def can_handle(cls, file_path: Path) -> bool:
        """判断是否能处理该文件

        Args:
            file_path: 文件路径

        Returns:
            True表示可以处理
        """
        return file_path.suffix.lower() in [
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'
        ]

    def load(self, file_path: Path) -> list[DocumentElement]:
        """加载图片文件，执行OCR、LLM描述、图表分析

        Args:
            file_path: 图片文件路径

        Returns:
            文档元素列表
        """
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        elements = []
        ocr_text = ""

        # Step 1: OCR提取文字
        if self._tesseract_available:
            ocr_text = self._ocr_with_tesseract(file_path)
            if ocr_text and ocr_text.strip():
                elements.append(DocumentElement(
                    content=ocr_text.strip(),
                    element_type=ElementType.IMAGE_DESCRIPTION,
                    metadata={
                        "ocr_engine": "tesseract",
                        "ocr_languages": OCR_LANGUAGES,
                        "content_type": "ocr_text",
                    },
                    source_file=str(file_path),
                ))

        # Step 2: 图表分析（如果启用）
        if CHART_ANALYSIS_ENABLED:
            chart_desc = self._analyze_chart(file_path, ocr_text)
            if chart_desc:
                elements.append(DocumentElement(
                    content=chart_desc,
                    element_type=ElementType.IMAGE_DESCRIPTION,
                    metadata={
                        "content_type": "chart_analysis",
                        "analysis_engine": "llm",
                    },
                    source_file=str(file_path),
                ))

        # Step 3: LLM生成图片描述（如果启用）
        if IMAGE_LLM_DESCRIPTION:
            llm_desc = generate_image_description(str(file_path), ocr_text)
            if llm_desc:
                elements.append(DocumentElement(
                    content=llm_desc,
                    element_type=ElementType.IMAGE_DESCRIPTION,
                    metadata={
                        "content_type": "llm_description",
                        "description_engine": "deepseek",
                    },
                    source_file=str(file_path),
                ))

        # 兜底：如果没有生成任何内容，添加占位描述
        if not elements:
            elements.append(DocumentElement(
                content=f"[图片: {file_path.name}]",
                element_type=ElementType.IMAGE_DESCRIPTION,
                metadata={
                    "ocr_engine": "none",
                    "content_type": "placeholder",
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
            from src.config import TESSERACT_CMD

            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang=OCR_LANGUAGES)
            return text
        except Exception as e:
            print(f"OCR失败 {file_path}: {e}")
            return ""

    def _analyze_chart(self, file_path: Path, ocr_text: str) -> str:
        """分析图表类型并生成结构化描述

        Args:
            file_path: 图片文件路径
            ocr_text: OCR文本

        Returns:
            图表描述文本
        """
        if self._chart_analyzer is None:
            from src.core.chart_analyzer import ChartAnalyzer
            self._chart_analyzer = ChartAnalyzer()

        if not self._chart_analyzer.is_enabled():
            return ""

        analysis = self._chart_analyzer.analyze(str(file_path), ocr_text)
        return self._chart_analyzer.format_as_description(analysis)

    @classmethod
    def supported_extensions(cls) -> list[str]:
        """返回支持的文件扩展名"""
        return ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
