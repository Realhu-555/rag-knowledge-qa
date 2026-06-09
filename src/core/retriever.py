"""检索引擎"""
from dataclasses import dataclass, field
from typing import Any

from src.config import RETRIEVAL_TOP_K, RRF_K


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


class Retriever:
    """向量检索"""

    def __init__(self, vector_store, embedder):
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = RETRIEVAL_TOP_K) -> list[RetrievalResult]:
        """语义检索"""
        # 将查询转换为向量
        query_embedding = self.embedder.embed_single(query)

        # 检索
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=top_k
        )

        # 转换结果格式
        retrieval_results = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                # 将距离转换为相似度分数（0-1）
                score = 1 - distance / 2 if distance <= 2 else 0
                retrieval_results.append(RetrievalResult(
                    content=doc,
                    metadata=metadata,
                    score=score
                ))

        return retrieval_results


class HybridRetriever:
    """混合检索（向量 + BM25）"""

    def __init__(self, vector_store, embedder):
        self.vector_store = vector_store
        self.embedder = embedder
        self.bm25_index = None
        self.bm25_docs = []

    def build_bm25_index(self, documents: list[str]):
        """构建BM25索引"""
        from rank_bm25 import BM25Okapi
        # 简单的中文分词（按字符）
        tokenized_docs = [list(doc) for doc in documents]
        self.bm25_index = BM25Okapi(tokenized_docs)
        self.bm25_docs = documents

    def retrieve(self, query: str, top_k: int = RETRIEVAL_TOP_K) -> list[RetrievalResult]:
        """混合检索"""
        # 向量检索
        vector_results = self._vector_search(query, top_k)

        # BM25检索
        bm25_results = self._bm25_search(query, top_k)

        # RRF融合
        return self._rrf_fusion(vector_results, bm25_results, top_k)

    def _vector_search(self, query: str, top_k: int) -> list[RetrievalResult]:
        """向量检索"""
        query_embedding = self.embedder.embed_single(query)
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=top_k
        )

        retrieval_results = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                retrieval_results.append(RetrievalResult(
                    content=doc,
                    metadata=metadata,
                    score=0.0  # 稍后由RRF计算
                ))
        return retrieval_results

    def _bm25_search(self, query: str, top_k: int) -> list[RetrievalResult]:
        """BM25检索"""
        if self.bm25_index is None:
            return []

        # 简单的中文分词
        tokenized_query = list(query)
        scores = self.bm25_index.get_scores(tokenized_query)

        # 获取top_k结果
        top_indices = scores.argsort()[-top_k:][::-1]

        results = []
        for idx in top_indices:
            if idx < len(self.bm25_docs):
                results.append(RetrievalResult(
                    content=self.bm25_docs[idx],
                    metadata={},
                    score=0.0
                ))
        return results

    def _rrf_fusion(
        self,
        vector_results: list[RetrievalResult],
        bm25_results: list[RetrievalResult],
        top_k: int,
        k: int = RRF_K
    ) -> list[RetrievalResult]:
        """RRF融合"""
        # 合并所有结果
        all_docs = {}
        for rank, result in enumerate(vector_results):
            doc_key = result.content[:100]  # 用前100字符作为key
            if doc_key not in all_docs:
                all_docs[doc_key] = {
                    "result": result,
                    "vector_rank": rank + 1,
                    "bm25_rank": len(bm25_results) + 1
                }
            else:
                all_docs[doc_key]["vector_rank"] = rank + 1

        for rank, result in enumerate(bm25_results):
            doc_key = result.content[:100]
            if doc_key not in all_docs:
                all_docs[doc_key] = {
                    "result": result,
                    "vector_rank": len(vector_results) + 1,
                    "bm25_rank": rank + 1
                }
            else:
                all_docs[doc_key]["bm25_rank"] = rank + 1

        # 计算RRF分数
        for doc_key in all_docs:
            info = all_docs[doc_key]
            rrf_score = 1 / (k + info["vector_rank"]) + 1 / (k + info["bm25_rank"])
            info["result"].score = rrf_score

        # 按RRF分数排序
        sorted_results = sorted(
            all_docs.values(),
            key=lambda x: x["result"].score,
            reverse=True
        )

        return [item["result"] for item in sorted_results[:top_k]]
