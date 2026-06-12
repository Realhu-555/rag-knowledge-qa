"""RAG引擎测试"""
from unittest.mock import Mock, patch

from src.core.rag_engine import RAGEngine


class TestRAGEngine:
    """RAG引擎测试"""

    @patch('src.core.rag_engine.QueryCache')
    @patch('src.core.rag_engine.Reranker')
    @patch('src.core.rag_engine.QueryUnderstander')
    @patch('src.core.rag_engine.Generator')
    @patch('src.core.rag_engine.Retriever')
    @patch('src.core.rag_engine.VectorStore')
    @patch('src.core.rag_engine.Embedder')
    def test_engine_initialization(self, mock_embedder, mock_store, mock_retriever,
                                    mock_gen, mock_qu, mock_reranker, mock_cache):
        """引擎初始化"""
        engine = RAGEngine(use_query_expansion=False, use_reranker=False)
        assert engine is not None

    @patch('src.core.rag_engine.QueryCache')
    @patch('src.core.rag_engine.Reranker')
    @patch('src.core.rag_engine.QueryUnderstander')
    @patch('src.core.rag_engine.Generator')
    @patch('src.core.rag_engine.Retriever')
    @patch('src.core.rag_engine.VectorStore')
    @patch('src.core.rag_engine.Embedder')
    def test_query_returns_response(self, mock_embedder_cls, mock_store_cls,
                                     mock_retriever_cls, mock_gen_cls,
                                     mock_qu_cls, mock_reranker_cls, mock_cache_cls):
        """查询返回响应"""
        mock_retriever = Mock()
        mock_gen = Mock()

        mock_retriever_cls.return_value = mock_retriever
        mock_gen_cls.return_value = mock_gen

        mock_retriever.retrieve.return_value = [
            Mock(content="参考内容", metadata={"source": "test.md", "section": "test"}, score=0.9)
        ]
        mock_gen.generate.return_value = {
            "answer": "这是回答",
            "usage": {"total_tokens": 100}
        }

        engine = RAGEngine(use_query_expansion=False, use_hyde=False, use_reranker=False)
        result = engine.query("什么是RAG？")

        assert result.answer
        assert result.sources is not None
        assert result.timing is not None
