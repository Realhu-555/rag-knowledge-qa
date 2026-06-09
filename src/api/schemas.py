"""Pydantic请求/响应模型"""
from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., description="用户问题")
    session_id: Optional[str] = Field(None, description="会话ID（多轮对话用）")
    top_k: Optional[int] = Field(5, description="返回前几条检索结果")
    use_hyde: Optional[bool] = Field(False, description="是否启用HyDE")


class Source(BaseModel):
    """引用来源"""
    file: str = Field(..., description="来源文件名")
    section: str = Field("", description="所属章节")
    content_type: str = Field("text", description="内容类型")
    chunk: str = Field(..., description="原文片段")
    score: float = Field(..., description="相关度分数")


class QueryResponse(BaseModel):
    """问答响应"""
    request_id: str = Field(..., description="请求ID")
    answer: str = Field(..., description="回答内容")
    sources: list[Source] = Field(default_factory=list, description="引用来源")
    usage: dict = Field(default_factory=dict, description="Token用量")
    timing: dict = Field(default_factory=dict, description="耗时统计")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field("ok", description="服务状态")
    version: str = Field("1.0.0", description="版本号")


class StatsResponse(BaseModel):
    """统计信息响应"""
    total_documents: int = Field(0, description="文档数")
    total_chunks: int = Field(0, description="知识片段数")


class DocumentInfo(BaseModel):
    """文档信息"""
    id: str = Field(..., description="文档ID")
    filename: str = Field(..., description="文件名")
    chunks: int = Field(0, description="chunk数")
    indexed_at: str = Field("", description="索引时间")


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: list[DocumentInfo] = Field(default_factory=list)
    total: int = Field(0, description="总数")


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="消息")
    document_id: Optional[str] = Field(None, description="文档ID")
