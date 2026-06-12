"""pytest fixtures for shared test configuration"""
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_llm():
    """Mock openai.OpenAI，返回固定响应。

    Usage in test::

        def test_something(mock_llm):
            gen = Generator()
            # mock_llm is already patched, gen.generate() will use it
    """
    mock_response = Mock()
    mock_response.choices = [
        Mock(message=Mock(content="这是基于知识库的测试回答[1]。"))
    ]
    mock_response.usage = Mock(
        prompt_tokens=50,
        completion_tokens=30,
        total_tokens=80,
    )

    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("openai.OpenAI", return_value=mock_client):
        yield mock_client
