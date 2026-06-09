"""LLM生成模块测试"""
import pytest
from unittest.mock import Mock, patch
from src.core.generator import Generator


class TestGenerator:
    """Generator测试"""

    def test_build_prompt(self):
        """构建prompt"""
        gen = Generator()
        sources = [
            {"content": "RAG是检索增强生成", "metadata": {"source": "rag.md", "section": "简介"}},
            {"content": "Embedding将文本转为向量", "metadata": {"source": "embed.md", "section": "定义"}}
        ]

        prompt = gen._build_prompt("什么是RAG？", sources)

        assert "什么是RAG？" in prompt
        assert "RAG是检索增强生成" in prompt
        assert "[1]" in prompt
        assert "[2]" in prompt
        assert "rag.md" in prompt

    def test_build_prompt_includes_rules(self):
        """prompt包含规则"""
        gen = Generator()
        prompt = gen._build_prompt("问题", [])

        assert "不要编造" in prompt
        assert "知识库中未找到" in prompt

    @patch('src.core.generator.OpenAI')
    def test_generate_calls_llm(self, mock_openai_class):
        """生成调用LLM"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="回答内容"))]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_client.chat.completions.create.return_value = mock_response

        gen = Generator()
        gen._init_client()

        result = gen.generate("问题", [{"content": "参考", "metadata": {}}])

        assert result["answer"] == "回答内容"
        assert result["usage"]["total_tokens"] == 30
