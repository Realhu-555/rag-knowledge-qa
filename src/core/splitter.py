"""智能切片"""
import re
from dataclasses import dataclass, field
from typing import Any

from src.config import CHUNK_SIZE, CHUNK_OVERLAP
from src.core.loaders.base import DocumentElement, ElementType


@dataclass
class Chunk:
    """切片结果"""
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SmartSplitter:
    """智能切片器：根据element_type选择策略

    - 表格/图片：不切分，整体保留
    - 文本：按标题切分，超长再按字数兜底
    """

    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        """初始化智能切片器

        Args:
            chunk_size: 切片大小
            chunk_overlap: 重叠大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._markdown_splitter = MarkdownSplitter(chunk_size, chunk_overlap)
        self._text_splitter = RecursiveCharacterSplitter(chunk_size, chunk_overlap)

    def split_elements(self, elements: list[DocumentElement]) -> list[Chunk]:
        """切分文档元素列表

        Args:
            elements: 文档元素列表

        Returns:
            切片结果列表
        """
        chunks = []

        for element in elements:
            element_chunks = self.split_element(element)
            chunks.extend(element_chunks)

        return chunks

    def split_element(self, element: DocumentElement) -> list[Chunk]:
        """根据元素类型选择切分策略

        Args:
            element: 文档元素

        Returns:
            切片结果列表
        """
        # 表格和图片不切分，整体保留
        if element.element_type in [ElementType.TABLE, ElementType.IMAGE_DESCRIPTION]:
            metadata = {
                **element.metadata,
                "element_type": element.element_type.value,
                "source_file": element.source_file,
                "page_number": element.page_number,
            }
            return [Chunk(content=element.content, metadata=metadata)]

        # 代码块不切分
        if element.element_type == ElementType.CODE:
            metadata = {
                **element.metadata,
                "element_type": element.element_type.value,
                "source_file": element.source_file,
                "page_number": element.page_number,
            }
            return [Chunk(content=element.content, metadata=metadata)]

        # 文本类型：使用Markdown切片器
        metadata = {
            **element.metadata,
            "element_type": element.element_type.value,
            "source_file": element.source_file,
            "page_number": element.page_number,
        }

        # 尝试作为Markdown切分
        chunks = self._markdown_splitter.split(element.content, metadata)

        # 如果只有一个chunk且内容较短，可能不是Markdown格式，使用通用文本切片
        if len(chunks) == 1 and len(element.content) < self.chunk_size // 2:
            chunks = self._text_splitter.split(element.content, metadata)

        return chunks


class MarkdownSplitter:
    """Markdown智能切片器：按标题切分，超长再按字数兜底"""

    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, content: str, metadata: dict[str, Any]) -> list[Chunk]:
        """切分Markdown内容"""
        # 按标题切分
        sections = self._split_by_headers(content)

        chunks = []
        for section in sections:
            section_content = section["content"].strip()
            if not section_content:
                continue

            # 如果section超长，再按字数切分
            if len(section_content) > self.chunk_size:
                sub_chunks = self._split_by_size(section_content)
                for i, sub_content in enumerate(sub_chunks):
                    chunk_metadata = {
                        **metadata,
                        "section": section.get("header", ""),
                        "chunk_index": i,
                        "content_type": "text",
                    }
                    chunks.append(Chunk(content=sub_content, metadata=chunk_metadata))
            else:
                chunk_metadata = {
                    **metadata,
                    "section": section.get("header", ""),
                    "chunk_index": len(chunks),
                    "content_type": "text",
                }
                chunks.append(Chunk(content=section_content, metadata=chunk_metadata))

        return chunks

    def _split_by_headers(self, content: str) -> list[dict[str, str]]:
        """按Markdown标题切分（保护代码块）"""
        # 匹配 # ## ### 标题
        header_pattern = r'^(#{1,3})\s+(.+)$'
        lines = content.split('\n')

        sections = []
        current_header = ""
        current_content = []
        in_code_block = False

        for line in lines:
            # 跟踪代码块状态
            stripped = line.strip()
            if stripped.startswith('```'):
                in_code_block = not in_code_block

            # 代码块内不切分
            if in_code_block:
                current_content.append(line)
                continue

            match = re.match(header_pattern, line, re.MULTILINE)
            if match:
                # 保存之前的section
                if current_content:
                    sections.append({
                        "header": current_header,
                        "content": '\n'.join(current_content)
                    })
                current_header = match.group(2).strip()
                current_content = [line]
            else:
                current_content.append(line)

        # 保存最后一个section
        if current_content:
            sections.append({
                "header": current_header,
                "content": '\n'.join(current_content)
            })

        return sections

    def _split_by_size(self, content: str) -> list[str]:
        """按字数切分，保留重叠"""
        if len(content) <= self.chunk_size:
            return [content]

        chunks = []
        start = 0
        while start < len(content):
            end = start + self.chunk_size
            chunk = content[start:end]
            chunks.append(chunk)
            # 下一个chunk从当前chunk末尾往前overlap个字符开始
            start = end - self.chunk_overlap

        return chunks


class RecursiveCharacterSplitter:
    """通用文本切片器：按段落→句子→字数优先级切分"""

    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "]

    def split(self, content: str, metadata: dict[str, Any]) -> list[Chunk]:
        """切分文本内容"""
        if len(content) <= self.chunk_size:
            return [Chunk(content=content, metadata=metadata)]

        chunks = []
        current_chunks = self._split_recursive(content, self.separators)

        for i, chunk_content in enumerate(current_chunks):
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
                "content_type": "text",
            }
            chunks.append(Chunk(content=chunk_content, metadata=chunk_metadata))

        return chunks

    def _split_recursive(self, content: str, separators: list[str]) -> list[str]:
        """递归切分"""
        if len(content) <= self.chunk_size:
            return [content]

        if not separators:
            # 没有分隔符了，直接按字数切
            return self._split_by_size(content)

        separator = separators[0]
        remaining_separators = separators[1:]

        parts = content.split(separator)
        chunks = []
        current_chunk = ""

        for part in parts:
            test_chunk = current_chunk + separator + part if current_chunk else part
            if len(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # 如果单个part超长，递归切分
                if len(part) > self.chunk_size:
                    chunks.extend(self._split_recursive(part, remaining_separators))
                    current_chunk = ""
                else:
                    current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_by_size(self, content: str) -> list[str]:
        """按字数切分"""
        chunks = []
        start = 0
        while start < len(content):
            end = start + self.chunk_size
            chunk = content[start:end]
            chunks.append(chunk)
            start = end - self.chunk_overlap
        return chunks
