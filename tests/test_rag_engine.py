"""RAG引擎测试"""
import pytest
from unittest.mock import Mock, patch
from src.core.rag_engine import RAGEngine


class TestRAGEngine:
    """RAG引擎测试"""

    @patch('src.core.rag_engine.Generator')
    @patch('src.core.rag_engine.Retriever')
    @patch('src.core.rag_engine.VectorStore')
    @patch('src.core.rag_engine.Embedder')
    def test_engine_initialization(self, mock_embedder, mock_store, mock_retriever, mock_gen):
        """引擎初始化"""
        engine = RAGEngine()
        assert engine is not None

    @patch('src.core.rag_engine.Generator')
    @patch('src.core.rag_engine.Retriever')
    @patch('src.core.rag_engine.VectorStore')
    @patch('src.core.rag_engine.Embedder')
    def test_query_returns_response(self, mock_embedder_cls, mock_store_cls, mock_retriever_cls, mock_gen_cls):
        """查询返回响应"""
        mock_retriever = Mock()
        mock_gen = Mock()

        mock_retriever_cls.return_value = mock_retriever
        mock_gen_cls.return_value = mock_gen

        mock_retriever.retrieve.return_value = [
            Mock(content="参考内容", metadata={"source": "test.md", "section": "test"}, score=0.9)
        ]
        mock_gen.generate.return_value = {
            "answer": "这是回答[1]",
            "usage": {"total_tokens": 100}
        }

        engine = RAGEngine()
        result = engine.query("什么是RAG？")

        assert result.answer
        assert result.sources is not None
        assert result.timing is not None
