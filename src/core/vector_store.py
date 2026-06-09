"""ChromaDB封装"""
from pathlib import Path

import chromadb
from chromadb.config import Settings

from src.config import CHROMA_DB_DIR


class VectorStore:
    """ChromaDB向量数据库封装"""

    def __init__(self, collection_name: str = "knowledge_base"):
        self.collection_name = collection_name
        self.client = None
        self.collection = None

    def _init_client(self):
        """初始化ChromaDB客户端"""
        if self.client is None:
            # 确保目录存在
            CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

            self.client = chromadb.PersistentClient(
                path=str(CHROMA_DB_DIR),
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

    def add(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None
    ) -> None:
        """添加文档到向量库"""
        self._init_client()
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict | None = None
    ) -> dict:
        """查询向量库"""
        self._init_client()
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
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
