"""RAG引擎"""
import time
from dataclasses import dataclass, field
from typing import Any

from src.core.embedder import Embedder
from src.core.vector_store import VectorStore
from src.core.retriever import Retriever
from src.core.generator import Generator
from src.core.query_understander import QueryUnderstander
from src.core.reranker import Reranker
from src.config import RETRIEVAL_TOP_K


@dataclass
class RAGResponse:
    """RAG响应"""
    answer: str
    sources: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    timing: dict = field(default_factory=dict)
    query_expansion: dict = field(default_factory=dict)


class RAGEngine:
    """RAG引擎：串联所有模块"""

    def __init__(self, use_query_expansion: bool = True, use_hyde: bool = False, use_reranker: bool = True):
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.retriever = Retriever(self.vector_store, self.embedder)
        self.generator = Generator()
        self.query_understander = QueryUnderstander()
        self.reranker = Reranker()

        # 功能开关
        self.use_query_expansion = use_query_expansion
        self.use_hyde = use_hyde
        self.use_reranker = use_reranker

    def query(self, question: str, top_k: int = RETRIEVAL_TOP_K) -> RAGResponse:
        """执行RAG问答"""
        start_time = time.time()
        timing = {}

        # 1. 查询理解
        query_start = time.time()
        expanded_queries = [question]
        entities = []
        hyde_query = None

        if self.use_query_expansion:
            expansion = self.query_understander.expand_query(question)
            expanded_queries = expansion.expanded_queries
            entities = expansion.entities

        if self.use_hyde:
            hyde_query = self.query_understander.generate_hyde(question)
            expanded_queries.append(hyde_query)

        timing["query_understanding_ms"] = round((time.time() - query_start) * 1000, 2)

        # 2. 多路检索
        retrieval_start = time.time()
        all_results = []

        for q in expanded_queries:
            results = self.retriever.retrieve(q, top_k)
            all_results.extend(results)

        # 去重（按内容前100字符判断）
        seen = set()
        unique_results = []
        for result in all_results:
            key = result.content[:100]
            if key not in seen:
                seen.add(key)
                unique_results.append(result)

        timing["retrieval_ms"] = round((time.time() - retrieval_start) * 1000, 2)

        # 3. ReRanker重排序
        rerank_start = time.time()
        if self.use_reranker and unique_results:
            # 准备reranker输入
            docs_for_rerank = [
                {"content": r.content, "metadata": r.metadata}
                for r in unique_results
            ]
            reranked = self.reranker.rerank(question, docs_for_rerank, top_k)
            final_results = reranked
        else:
            final_results = unique_results[:top_k]

        timing["rerank_ms"] = round((time.time() - rerank_start) * 1000, 2)

        # 4. 准备sources
        sources = []
        for result in final_results:
            sources.append({
                "content": result.content,
                "metadata": result.metadata,
                "score": result.score
            })

        # 5. 生成
        generation_start = time.time()
        if not sources:
            answer = "知识库中未找到相关信息"
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        else:
            result = self.generator.generate(question, sources)
            answer = result["answer"]
            usage = result["usage"]
        timing["generation_ms"] = round((time.time() - generation_start) * 1000, 2)

        total_time = (time.time() - start_time) * 1000
        timing["total_ms"] = round(total_time, 2)

        return RAGResponse(
            answer=answer,
            sources=sources,
            usage=usage,
            timing=timing,
            query_expansion={
                "expanded_queries": expanded_queries,
                "entities": entities,
                "hyde_query": hyde_query
            }
        )
