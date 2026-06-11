"""ChromaDB封装 — 支持多collection（按kb_id隔离）"""
import chromadb
from chromadb.config import Settings

from src.config import CHROMA_DB_DIR

# 默认 collection 名称（未指定 kb_id 时使用）
DEFAULT_COLLECTION = "knowledge_base"


class VectorStore:
    """ChromaDB向量数据库封装

    支持按 kb_id 隔离数据：每个知识库对应一个独立的 ChromaDB collection。
    """

    def __init__(self, collection_name: str = DEFAULT_COLLECTION):
        self.collection_name = collection_name
        self.client = None
        self.collection = None

    def _init_client(self):
        """初始化ChromaDB客户端"""
        if self.client is None:
            CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=str(CHROMA_DB_DIR),
                settings=Settings(anonymized_telemetry=False),
            )
        if self.collection is None:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

    # ------------------------------------------------------------------
    # 多 collection 支持
    # ------------------------------------------------------------------

    def get_collection_for_kb(self, kb_id: str | None = None) -> chromadb.Collection:
        """获取指定知识库对应的 collection；kb_id=None 返回默认 collection"""
        self._init_client()
        name = kb_id if kb_id else DEFAULT_COLLECTION
        # collection 名称只允许字母数字下划线
        safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
        return self.client.get_or_create_collection(
            name=safe_name,
            metadata={"hnsw:space": "cosine"},
        )

    def set_kb(self, kb_id: str | None = None) -> None:
        """切换当前操作的知识库"""
        self.collection_name = kb_id or DEFAULT_COLLECTION
        self.collection = None  # 延迟重建

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> None:
        """添加文档到向量库"""
        self._init_client()
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict | None = None,
    ) -> dict:
        """查询向量库"""
        self._init_client()
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )

    def delete(self, ids: list[str]) -> None:
        """删除文档"""
        self._init_client()
        self.collection.delete(ids=ids)

    def count(self) -> int:
        """获取文档总数"""
        self._init_client()
        return self.collection.count()

    def get_all(self) -> dict:
        """获取所有文档"""
        self._init_client()
        return self.collection.get()
