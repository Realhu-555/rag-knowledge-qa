"""查询理解模块测试"""
from unittest.mock import Mock, patch
from src.core.query_understander import QueryUnderstander, QueryExpansion


class TestQueryExpansion:
    """QueryExpansion数据类测试"""

    def test_creation(self):
        """创建QueryExpansion"""
        qe = QueryExpansion(
            original_query="什么是RAG？",
            expanded_queries=["RAG定义", "RAG原理"],
            entities=["RAG"],
            intent="询问RAG概念"
        )
        assert qe.original_query == "什么是RAG？"
        assert len(qe.expanded_queries) == 2

    def test_default_values(self):
        """默认值"""
        qe = QueryExpansion(original_query="test")
        assert qe.expanded_queries == []
        assert qe.entities == []
        assert qe.intent == ""


class TestQueryUnderstander:
    """QueryUnderstander测试"""

    @patch('src.core.query_understander.OpenAI')
    def test_expand_query(self, mock_openai_class):
        """查询扩展"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"expanded_queries": ["RAG定义", "检索增强"], "entities": ["RAG"], "intent": "询问概念"}'))]
        mock_client.chat.completions.create.return_value = mock_response

        understander = QueryUnderstander()
        result = understander.expand_query("什么是RAG？")

        assert isinstance(result, QueryExpansion)
        assert result.original_query == "什么是RAG？"
        assert len(result.expanded_queries) == 2

    @patch('src.core.query_understander.OpenAI')
    def test_expand_query_parse_error(self, mock_openai_class):
        """查询扩展JSON解析失败时返回原始查询"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="无效的响应"))]
        mock_client.chat.completions.create.return_value = mock_response

        understander = QueryUnderstander()
        result = understander.expand_query("测试")

        assert result.expanded_queries == ["测试"]

    @patch('src.core.query_understander.OpenAI')
    def test_generate_hyde(self, mock_openai_class):
        """HyDE生成"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="RAG是一种检索增强生成技术..."))]
        mock_client.chat.completions.create.return_value = mock_response

        understander = QueryUnderstander()
        result = understander.generate_hyde("什么是RAG？")

        assert "RAG" in result
