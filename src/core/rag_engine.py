"""RAG引擎 — 串联所有模块 + M4链路追踪/指标"""
import time
from dataclasses import dataclass, field
from typing import Any

from src.core.embedder import Embedder
from src.core.vector_store import VectorStore
from src.core.retriever import Retriever, HybridRetriever
from src.core.generator import Generator
from src.core.query_understander import QueryUnderstander
from src.core.reranker import Reranker
from src.core.tracer import Trace
from src.core.metrics import metrics
from src.api.logging_config import log_retrieval, log_llm_call
from src.config import RETRIEVAL_TOP_K, USE_HYBRID_RETRIEVAL, RELEVANCE_THRESHOLD
from src.core.query_cache import QueryCache


@dataclass
class RAGResponse:
    """RAG响应"""
    answer: str
    sources: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    timing: dict = field(default_factory=dict)
    query_expansion: dict = field(default_factory=dict)
    trace_id: str = ""


class RAGEngine:
    """RAG引擎：串联所有模块"""

    def __init__(self, use_query_expansion: bool = True, use_hyde: bool = False, use_reranker: bool = True):
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.generator = Generator()
        self.query_understander = QueryUnderstander()
        self.reranker = Reranker()

        # 根据配置选择检索器：混合检索（向量+BM25）或纯向量检索
        if USE_HYBRID_RETRIEVAL:
            self.retriever = HybridRetriever(self.vector_store, self.embedder)
            self._build_bm25_index()
        else:
            self.retriever = Retriever(self.vector_store, self.embedder)

        # 功能开关
        self.use_query_expansion = use_query_expansion
        self.use_hyde = use_hyde
        self.use_reranker = use_reranker

        # M5: 查询缓存
        self.query_cache = QueryCache()

    def _build_bm25_index(self):
        """从向量库加载所有文档，构建BM25索引"""
        if not isinstance(self.retriever, HybridRetriever):
            return
        try:
            all_data = self.vector_store.get_all()
            if all_data and all_data.get("documents"):
                documents = all_data["documents"]
                self.retriever.build_bm25_index(documents)
                print(f"BM25索引构建完成，共 {len(documents)} 个文档")
            else:
                print("向量库为空，跳过BM25索引构建")
        except Exception as e:
            print(f"BM25索引构建失败: {e}，回退到纯向量检索")
            self.retriever = Retriever(self.vector_store, self.embedder)

    def query(self, question: str, top_k: int = RETRIEVAL_TOP_K,
              history: list[dict] | None = None,
              user_id: str = "") -> RAGResponse:
        """执行RAG问答

        Args:
            question: 用户问题
            top_k: 检索结果数量
            history: 对话历史，注入LLM用于多轮上下文
            user_id: 调用用户ID（用于trace）
        """
        # ---- M4: 启动 trace ----
        trace = Trace(question, user_id=user_id)
        metrics.inc_counter("total_queries")

        # ---- M5: 缓存命中检查 ----
        cached = self.query_cache.get(question, top_k)
        if cached is not None:
            sources = [s for s in cached if s.get("score", 0) >= RELEVANCE_THRESHOLD]
            if sources:
                answer = self.generator.generate(question, sources, history=history)["answer"]
            else:
                answer = "知识库中未找到相关信息"
            return RAGResponse(
                answer=answer,
                sources=cached,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                timing={"total_ms": 0, "cached": True},
                trace_id=trace.trace_id,
            )

        start_time = time.time()
        timing = {}

        try:
            # 1. 查询理解
            span = trace.start_span("query_understanding")
            query_start = time.time()
            expanded_queries = [question]
            entities = []
            hyde_query = None

            if self.use_query_expansion:
                expansion = self.query_understander.expand_query(question)
                expanded_queries = expansion.expanded_queries
                entities = expansion.entities

            # HyDE：用假设回答做向量检索
            hyde_results = []
            if self.use_hyde:
                hyde_text = self.query_understander.generate_hyde(question)
                hyde_embedding = self.embedder.embed_single(hyde_text)
                hyde_retrieval = self.vector_store.query(
                    query_embedding=hyde_embedding,
                    n_results=top_k
                )
                if hyde_retrieval and hyde_retrieval.get("documents"):
                    from src.core.retriever import RetrievalResult
                    for i, doc in enumerate(hyde_retrieval["documents"][0]):
                        metadata = hyde_retrieval["metadatas"][0][i] if hyde_retrieval.get("metadatas") else {}
                        hyde_results.append(RetrievalResult(
                            content=doc,
                            metadata=metadata,
                            score=0.5
                        ))

            timing["query_understanding_ms"] = round((time.time() - query_start) * 1000, 2)
            trace.end_span({
                "expanded_queries": expanded_queries,
                "entities": entities,
                "hyde_used": self.use_hyde,
            })

            # 2. 多路检索
            span = trace.start_span("retrieval")
            retrieval_start = time.time()
            all_results = []

            for q in expanded_queries:
                results = self.retriever.retrieve(q, top_k)
                all_results.extend(results)

            # 合并HyDE检索结果
            all_results.extend(hyde_results)

            # 去重（用hash）
            import hashlib
            seen = set()
            unique_results = []
            for result in all_results:
                key = hashlib.md5(result.content.encode()).hexdigest()
                if key not in seen:
                    seen.add(key)
                    unique_results.append(result)

            timing["retrieval_ms"] = round((time.time() - retrieval_start) * 1000, 2)
            metrics.record_histogram("retrieval_latency_ms", timing["retrieval_ms"])
            log_retrieval(question, top_k, len(unique_results), timing["retrieval_ms"])
            trace.end_span({
                "unique_results": len(unique_results),
                "top_k": top_k,
            })

            # 3. ReRanker重排序
            span = trace.start_span("rerank")
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
            trace.end_span({
                "reranker_used": self.use_reranker,
                "final_count": len(final_results),
            })

            # 3.5 M5: 阈值过滤
            final_results = [r for r in final_results if r.score >= RELEVANCE_THRESHOLD]

            # 4. 准备sources
            sources = []
            for result in final_results:
                sources.append({
                    "content": result.content,
                    "metadata": result.metadata,
                    "score": result.score
                })

            # 5. 生成
            span = trace.start_span("generation")
            generation_start = time.time()
            if not sources:
                answer = "知识库中未找到相关信息"
                usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            else:
                result = self.generator.generate(question, sources, history=history)
                answer = result["answer"]
                usage = result["usage"]
                # LLM调用日志
                if "error" not in result:
                    log_llm_call(
                        model="deepseek-chat",
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        latency_ms=timing.get("generation_ms", 0),
                    )
            timing["generation_ms"] = round((time.time() - generation_start) * 1000, 2)
            metrics.record_histogram("generation_latency_ms", timing["generation_ms"])
            trace.end_span({
                "model": "deepseek-chat",
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            })

            total_time = (time.time() - start_time) * 1000
            timing["total_ms"] = round(total_time, 2)
            metrics.record_histogram("query_latency_ms", total_time)
            metrics.inc_counter("total_tokens_used", usage.get("total_tokens", 0))

            # M5: 写入缓存
            self.query_cache.set(question, top_k, sources)

            return RAGResponse(
                answer=answer,
                sources=sources,
                usage=usage,
                timing=timing,
                query_expansion={
                    "expanded_queries": expanded_queries,
                    "entities": entities,
                    "hyde_query": hyde_query
                },
                trace_id=trace.trace_id,
            )

        except Exception as e:
            trace.status = "error"
            metrics.inc_counter("total_errors")
            raise
        finally:
            trace.finish()
