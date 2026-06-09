"""切片模块测试"""
import pytest
from src.core.splitter import MarkdownSplitter, RecursiveCharacterSplitter, Chunk


class TestMarkdownSplitter:
    """Markdown切片器测试"""

    def test_split_by_headers(self):
        """按标题切分"""
        splitter = MarkdownSplitter(chunk_size=1000)
        content = """# 标题一
这是标题一的内容

## 标题二
这是标题二的内容

### 标题三
这是标题三的内容"""

        chunks = splitter.split(content, {"source": "test.md"})

        assert len(chunks) == 3
        assert chunks[0].metadata["section"] == "标题一"
        assert chunks[1].metadata["section"] == "标题二"
        assert chunks[2].metadata["section"] == "标题三"

    def test_split_long_section(self):
        """超长section按字数切分"""
        splitter = MarkdownSplitter(chunk_size=50, chunk_overlap=10)
        content = "# 标题\n" + "这是一段很长的内容。" * 20

        chunks = splitter.split(content, {"source": "test.md"})

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.content) <= 60  # chunk_size + overlap

    def test_empty_content(self):
        """空内容返回空列表"""
        splitter = MarkdownSplitter()
        chunks = splitter.split("", {"source": "test.md"})
        assert chunks == []

    def test_metadata_preserved(self):
        """元数据保留"""
        splitter = MarkdownSplitter()
        content = "# 标题\n内容"
        metadata = {"source": "test.md", "custom": "value"}

        chunks = splitter.split(content, metadata)

        assert chunks[0].metadata["source"] == "test.md"
        assert chunks[0].metadata["custom"] == "value"
        assert "section" in chunks[0].metadata
        assert "chunk_index" in chunks[0].metadata


class TestRecursiveCharacterSplitter:
    """递归字符切片器测试"""

    def test_short_content_no_split(self):
        """短内容不切分"""
        splitter = RecursiveCharacterSplitter(chunk_size=100)
        content = "这是短内容"

        chunks = splitter.split(content, {"source": "test.txt"})

        assert len(chunks) == 1
        assert chunks[0].content == content

    def test_split_by_paragraphs(self):
        """按段落切分"""
        splitter = RecursiveCharacterSplitter(chunk_size=20)
        content = "第一段内容很长需要切分\n\n第二段内容很长需要切分\n\n第三段内容很长需要切分"

        chunks = splitter.split(content, {"source": "test.txt"})

        assert len(chunks) >= 2

    def test_split_long_text(self):
        """长文本切分"""
        splitter = RecursiveCharacterSplitter(chunk_size=30, chunk_overlap=5)
        content = "这是测试内容。" * 20

        chunks = splitter.split(content, {"source": "test.txt"})

        assert len(chunks) > 1


class TestChunk:
    """Chunk数据类测试"""

    def test_chunk_creation(self):
        """创建Chunk"""
        chunk = Chunk(content="测试内容", metadata={"key": "value"})
        assert chunk.content == "测试内容"
        assert chunk.metadata == {"key": "value"}

    def test_chunk_default_metadata(self):
        """默认元数据为空字典"""
        chunk = Chunk(content="测试内容")
        assert chunk.metadata == {}
