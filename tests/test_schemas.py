"""Pydantic模型测试"""
import pytest
from src.api.schemas import (
    QueryRequest,
    QueryResponse,
    Source,
    HealthResponse,
)


class TestQueryRequest:
    """QueryRequest测试"""

    def test_valid_request(self):
        """有效请求"""
        req = QueryRequest(question="什么是RAG？")
        assert req.question == "什么是RAG？"
        assert req.session_id is None
        assert req.use_hyde is False

    def test_with_options(self):
        """带选项的请求"""
        req = QueryRequest(
            question="测试",
            session_id="session123",
            use_hyde=True
        )
        assert req.session_id == "session123"
        assert req.use_hyde is True


class TestQueryResponse:
    """QueryResponse测试"""

    def test_valid_response(self):
        """有效响应"""
        resp = QueryResponse(
            request_id="req123",
            answer="RAG是检索增强生成[1]",
            sources=[],
            timing={"total_ms": 100}
        )
        assert "RAG" in resp.answer


class TestSource:
    """Source测试"""

    def test_source_creation(self):
        """创建Source"""
        source = Source(
            file="rag.md",
            section="简介",
            content_type="text",
            chunk="RAG是...",
            score=0.95
        )
        assert source.file == "rag.md"
        assert source.score == 0.95


class TestHealthResponse:
    """HealthResponse测试"""

    def test_health_response(self):
        """健康检查响应"""
        resp = HealthResponse(
            status="ok",
            version="1.0.0"
        )
        assert resp.status == "ok"
        assert resp.version == "1.0.0"
