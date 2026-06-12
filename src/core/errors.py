"""RAG系统错误类型"""


class RAGError(Exception):
    """RAG错误基类"""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class RetrievalError(RAGError):
    """检索错误"""

    def __init__(self, message: str = "检索失败", details: dict | None = None):
        super().__init__(code="RETRIEVAL_ERROR", message=message, details=details)


class GenerationError(RAGError):
    """生成错误"""

    def __init__(self, message: str = "LLM生成失败", details: dict | None = None):
        super().__init__(code="GENERATION_ERROR", message=message, details=details)


class EmbeddingError(RAGError):
    """Embedding错误"""

    def __init__(self, message: str = "Embedding计算失败", details: dict | None = None):
        super().__init__(code="EMBEDDING_ERROR", message=message, details=details)


class IndexBuildError(RAGError):
    """索引构建错误"""

    def __init__(self, message: str = "索引构建失败", details: dict | None = None):
        super().__init__(code="INDEX_BUILD_ERROR", message=message, details=details)
