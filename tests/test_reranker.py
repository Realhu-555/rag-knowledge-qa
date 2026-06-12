"""ReRanker模块测试"""
from unittest.mock import Mock, patch
from src.core.reranker import Reranker, RerankResult


class TestRerankResult:
    """RerankResult数据类测试"""

    def test_creation(self):
        """创建RerankResult"""
        result = RerankResult(
            content="测试内容",
            metadata={"source": "test.md"},
            score=0.95
        )
        assert result.content == "测试内容"
        assert result.score == 0.95

    def test_default_values(self):
        """默认值"""
        result = RerankResult(content="test")
        assert result.metadata == {}
        assert result.score == 0.0


class TestReranker:
    """Reranker测试"""

    def test_rerank_empty_documents(self):
        """空文档列表返回空结果"""
        reranker = Reranker()
        result = reranker.rerank("query", [], top_k=5)
        assert result == []

    @patch('src.core.reranker.CrossEncoder')
    def test_rerank_returns_sorted_results(self, mock_cross_encoder_class):
        """重排序返回排序后的结果"""
        mock_model = Mock()
        mock_cross_encoder_class.return_value = mock_model
        mock_model.predict.return_value = [0.3, 0.9, 0.6]

        documents = [
            {"content": "文档A", "metadata": {"source": "a.md"}},
            {"content": "文档B", "metadata": {"source": "b.md"}},
            {"content": "文档C", "metadata": {"source": "c.md"}}
        ]

        reranker = Reranker()
        results = reranker.rerank("测试查询", documents, top_k=3)

        assert len(results) == 3
        assert results[0].content == "文档B"
        assert results[0].score == 0.9

    @patch('src.core.reranker.CrossEncoder')
    def test_rerank_limits_top_k(self, mock_cross_encoder_class):
        """重排序限制返回数量"""
        mock_model = Mock()
        mock_cross_encoder_class.return_value = mock_model
        mock_model.predict.return_value = [0.5, 0.8, 0.3, 0.9, 0.7]

        documents = [{"content": f"文档{i}"} for i in range(5)]

        reranker = Reranker()
        results = reranker.rerank("查询", documents, top_k=2)

        assert len(results) == 2
        assert results[0].score >= results[1].score
