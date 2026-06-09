"""API路由"""
import uuid
from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas import (
    QueryRequest, QueryResponse, Source,
    HealthResponse, StatsResponse,
    DocumentListResponse, DocumentInfo,
    UploadResponse
)
from src.api.auth import verify_api_key, require_role, create_api_key
from src.core.rag_engine import RAGEngine
from src.core.vector_store import VectorStore
from src.core.session import SessionManager

router = APIRouter(prefix="/api/v1")

# 初始化组件
rag_engine = RAGEngine()
vector_store = VectorStore()
session_manager = SessionManager()


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    key_info: dict = Depends(verify_api_key)
):
    """知识库问答（核心接口）"""
    # 生成请求ID
    request_id = f"req_{uuid.uuid4().hex[:12]}"

    # 获取或创建会话
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"

    # 添加用户消息到会话
    session_manager.add_message(session_id, "user", request.question)

    # 执行RAG问答
    response = rag_engine.query(request.question, top_k=request.top_k)

    # 添加助手回复到会话
    session_manager.add_message(session_id, "assistant", response.answer)

    # 转换sources格式
    sources = [
        Source(
            file=s["metadata"].get("source", "未知"),
            section=s["metadata"].get("section", ""),
            content_type=s["metadata"].get("content_type", "text"),
            chunk=s["content"],
            score=s["score"]
        )
        for s in response.sources
    ]

    return QueryResponse(
        request_id=request_id,
        answer=response.answer,
        sources=sources,
        usage=response.usage,
        timing=response.timing
    )


@router.get("/health", response_model=HealthResponse)
async def health():
    """健康检查"""
    return HealthResponse(status="ok", version="1.0.0")


@router.get("/stats", response_model=StatsResponse)
async def stats(
    key_info: dict = Depends(verify_api_key)
):
    """知识库统计"""
    from src.config import DATA_DIR
    total_documents = len(list(DATA_DIR.rglob("*.md")))
    total_chunks = vector_store.count()
    return StatsResponse(
        total_documents=total_documents,
        total_chunks=total_chunks
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    key_info: dict = Depends(verify_api_key)
):
    """查看文档列表"""
    # TODO: 实现文档列表
    return DocumentListResponse(documents=[], total=0)


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(
    key_info: dict = Depends(require_role("writer"))
):
    """上传文档"""
    # TODO: 实现文档上传
    return UploadResponse(
        success=False,
        message="功能尚未实现"
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    key_info: dict = Depends(require_role("writer"))
):
    """删除文档"""
    # TODO: 实现文档删除
    raise HTTPException(status_code=501, detail="功能尚未实现")


@router.post("/keys")
async def create_key(
    role: str = "reader",
    key_info: dict = Depends(require_role("admin"))
):
    """创建API Key（仅管理员）"""
    new_key = create_api_key(role)
    return {"key": new_key["key"], "role": new_key["role"]}
