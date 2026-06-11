"""检索模块测试"""
import pytest
from unittest.mock import Mock
from src.core.retriever import Retriever, RetrievalResult

jieba = pytest.importorskip("jieba")
from src.core.retriever import HybridRetriever


class TestRetriever:
    """向量检索器测试"""

    def test_retrieve_returns_results(self):
        """检索返回结果"""
        mock_store = Mock()
        mock_embedder = Mock()

        mock_embedder.embed_single.return_value = [0.1, 0.2, 0.3]
        mock_store.query.return_value = {
            "documents": [["文档1", "文档2"]],
            "metadatas": [[{"source": "a.md"}, {"source": "b.md"}]],
            "distances": [[0.5, 1.0]]
        }

        retriever = Retriever(mock_store, mock_embedder)
        results = retriever.retrieve("测试查询", top_k=2)

        assert len(results) == 2
        assert results[0].content == "文档1"
        assert results[0].score > 0

    def test_retrieve_empty_results(self):
        """空结果"""
        mock_store = Mock()
        mock_embedder = Mock()

        mock_embedder.embed_single.return_value = [0.1]
        mock_store.query.return_value = {"documents": [[]]}

        retriever = Retriever(mock_store, mock_embedder)
        results = retriever.retrieve("测试查询")

        assert results == []


class TestHybridRetriever:
    """混合检索器测试"""

    def test_build_bm25_index(self):
        """构建BM25索引"""
        mock_store = Mock()
        mock_embedder = Mock()

        retriever = HybridRetriever(mock_store, mock_embedder)
        retriever.build_bm25_index(["文档1", "文档2", "文档3"])

        assert retriever.bm25_index is not None
        assert len(retriever.bm25_docs) == 3

    def test_bm25_search(self):
        """BM25检索"""
        mock_store = Mock()
        mock_embedder = Mock()

        retriever = HybridRetriever(mock_store, mock_embedder)
        retriever.build_bm25_index(["RAG是检索增强生成", "Embedding是向量化", "LLM是大语言模型"])

        results = retriever._bm25_search("RAG", top_k=2)

        assert len(results) > 0
        assert "RAG" in results[0].content

    def test_rrf_fusion(self):
        """RRF融合"""
        mock_store = Mock()
        mock_embedder = Mock()

        retriever = HybridRetriever(mock_store, mock_embedder)

        vector_results = [
            RetrievalResult(content="文档A", metadata={}, score=0),
            RetrievalResult(content="文档B", metadata={}, score=0)
        ]
        bm25_results = [
            RetrievalResult(content="文档A", metadata={}, score=0),
            RetrievalResult(content="文档C", metadata={}, score=0)
        ]

        fused = retriever._rrf_fusion(vector_results, bm25_results, top_k=3)

        assert len(fused) == 3
        assert fused[0].content == "文档A"
        assert fused[0].score > 0
