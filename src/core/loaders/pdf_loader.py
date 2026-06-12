"""PDF文档加载器"""
from pathlib import Path

from src.core.loaders.base import BaseLoader, DocumentElement, ElementType


def _extract_table_text(table) -> str:
    """将pdfplumber表格转换为Markdown格式

    Args:
        table: pdfplumber表格（list of rows），每行是 cell 列表

    Returns:
        Markdown格式的表格字符串
    """
    if not table:
        return ""

    # pdfplumber extract_tables() 直接返回 list[list[list|None]]
    rows = table
    if not rows:
        return ""

    # 清理单元格文本
    cleaned_rows = []
    for row in rows:
        cleaned_row = []
        for cell in row:
            cell_text = str(cell).replace('\n', ' ').strip() if cell else ""
            cleaned_row.append(cell_text)
        cleaned_rows.append(cleaned_row)

    if not cleaned_rows:
        return ""

    # 确保所有行列数一致
    max_cols = max(len(row) for row in cleaned_rows)
    for row in cleaned_rows:
        while len(row) < max_cols:
            row.append("")

    # 构建Markdown表格
    lines = []
    # 表头
    lines.append("| " + " | ".join(cleaned_rows[0]) + " |")
    # 分隔符
    lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    # 数据行
    for row in cleaned_rows[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


class PdfLoader(BaseLoader):
    """PDF文档加载器，按页提取文本和表格"""

    @classmethod
    def can_handle(cls, file_path: Path) -> bool:
        """判断是否能处理该文件

        Args:
            file_path: 文件路径

        Returns:
            True表示可以处理
        """
        return file_path.suffix.lower() == '.pdf'

    def load(self, file_path: Path) -> list[DocumentElement]:
        """加载PDF文档

        Args:
            file_path: PDF文件路径

        Returns:
            文档元素列表
        """
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        try:
            import pdfplumber
        except ImportError:
            raise ImportError("请安装pdfplumber: uv pip install pdfplumber")

        elements = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # 提取文本
                text = page.extract_text()
                if text and text.strip():
                    elements.append(DocumentElement(
                        content=text.strip(),
                        element_type=ElementType.TEXT,
                        metadata={
                            "page": page_num,
                            "element": "text",
                        },
                        source_file=str(file_path),
                        page_number=page_num,
                    ))

                # 提取表格
                tables = page.extract_tables()
                for table_idx, table in enumerate(tables):
                    markdown_table = _extract_table_text(table)
                    if markdown_table:
                        elements.append(DocumentElement(
                            content=markdown_table,
                            element_type=ElementType.TABLE,
                            metadata={
                                "page": page_num,
                                "table_index": table_idx,
                                "element": "table",
                            },
                            source_file=str(file_path),
                            page_number=page_num,
                        ))

        return elements

    @classmethod
    def supported_extensions(cls) -> list[str]:
        """返回支持的文件扩展名"""
        return ['.pdf']
