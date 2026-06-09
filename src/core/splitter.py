"""智能切片"""
import re
from dataclasses import dataclass, field
from typing import Any

from src.config import CHUNK_SIZE, CHUNK_OVERLAP


@dataclass
class Chunk:
    """切片结果"""
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


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
        """按Markdown标题切分"""
        # 匹配 # ## ### 标题
        header_pattern = r'^(#{1,3})\s+(.+)$'
        lines = content.split('\n')

        sections = []
        current_header = ""
        current_content = []

        for line in lines:
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
