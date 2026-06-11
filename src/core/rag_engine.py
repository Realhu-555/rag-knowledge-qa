"""RAG引擎 — 串联所有模块 + M4链路追踪/指标 + M8对话增强"""
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
from src.config import (
    USE_CONVERSATION_SUMMARY,
    USE_INTENT_CLASSIFICATION,
    FOLLOWUP_SCORE_THRESHOLD,
)


@dataclass
class RAGResponse:
    """RAG响应"""
    answer: str
    sources: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    timing: dict = field(default_factory=dict)
    query_expansion: dict = field(default_factory=dict)
    trace_id: str = ""
    is_followup: bool = False  # M8: 是否为主动追问
    intent: str = "query"     # M8: 意图类型


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

        # M8: 意图识别
        self._intent_classifier = None

    def _get_intent_classifier(self):
        """懒加载意图分类器"""
        if self._intent_classifier is None:
            from src.core.intent_classifier import IntentClassifier
            self._intent_classifier = IntentClassifier()
        return self._intent_classifier

    def _generate_followup(self, question: str) -> str:
        """生成主动追问回复"""
        self.generator._init_client()
        prompt = (
            f"用户问了一个问题：{question}\n"
            "但知识库中没有找到足够相关的信息来回答。\n"
            "请用友好的语气引导用户提供更具体的信息。"
            "例如：'您能再具体描述一下您想了解的方面吗？' 或 "
            "'您能否提供更多细节，比如具体的技术名称或场景？'\n"
            "只输出追问语句，不要加多余的解释。"
        )
        try:
            from src.config import DEEPSEEK_MODEL
            response = self.generator.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return "您能再具体描述一下您想了解的内容吗？这样我能更准确地帮您查找。"

    def classify_intent(self, question: str, has_history: bool = False) -> str:
        """M8: 识别用户意图

        Returns:
            意图字符串: "query" / "followup" / "chitchat" / "feedback"
        """
        if not USE_INTENT_CLASSIFICATION:
            return "query"
        classifier = self._get_intent_classifier()
        result = classifier.classify(question, has_history)
        return result.intent.value

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
              summary: str = "",
              user_id: str = "") -> RAGResponse:
        """执行RAG问答

        Args:
            question: 用户问题
            top_k: 检索结果数量
            history: 对话历史，注入LLM用于多轮上下文
            summary: M8: 对话摘要
            user_id: 调用用户ID（用于trace）
        """
        # ---- M4: 启动 trace ----
        trace = Trace(question, user_id=user_id)
        metrics.inc_counter("total_queries")

        # ---- M8: 意图识别 ----
        has_history = bool(history)
        intent = self.classify_intent(question, has_history)

        if intent == "chitchat":
            # 闲聊：不走RAG，直接LLM回答
            result = self.generator.generate(
                question, sources=[], history=history, summary=summary,
            )
            return RAGResponse(
                answer=result["answer"],
                sources=[],
                usage=result.get("usage", {}),
                timing={"total_ms": 0},
                trace_id=trace.trace_id,
                intent="chitchat",
            )

        if intent == "feedback":
            # 反馈：记录并给出友好提示
            return RAGResponse(
                answer="感谢您的反馈！我会努力改进回答质量。请问还有其他问题吗？",
                sources=[],
                usage={},
                timing={"total_ms": 0},
                trace_id=trace.trace_id,
                intent="feedback",
            )

        # ---- M5: 缓存命中检查 ----
        cached = self.query_cache.get(question, top_k)
        if cached is not None:
            sources = [s for s in cached if s.get("score", 0) >= RELEVANCE_THRESHOLD]
            if sources:
                answer = self.generator.generate(
                    question, sources, history=history, summary=summary,
                )["answer"]
            else:
                answer = "知识库中未找到相关信息"
            return RAGResponse(
                answer=answer,
                sources=cached,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                timing={"total_ms": 0, "cached": True},
                trace_id=trace.trace_id,
                intent=intent,
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
            pre_filter_count = len(final_results)
            final_results = [r for r in final_results if r.score >= RELEVANCE_THRESHOLD]

            # 4. 准备sources
            sources = []
            for result in final_results:
                sources.append({
                    "content": result.content,
                    "metadata": result.metadata,
                    "score": result.score
                })

            # ---- M8: 主动追问检测 ----
            # 所有chunk分数都低于阈值（或过滤后无结果），且过滤前有结果说明检索到了但不相关
            is_followup = False
            if not sources and pre_filter_count > 0:
                # 检索到了结果但全部低于阈值 → 可能需要追问
                max_score = max(r.score for r in final_results) if final_results else 0
                if max_score < FOLLOWUP_SCORE_THRESHOLD and has_history:
                    followup_answer = self._generate_followup(question)
                    return RAGResponse(
                        answer=followup_answer,
                        sources=[],
                        usage={},
                        timing=timing,
                        trace_id=trace.trace_id,
                        is_followup=True,
                        intent=intent,
                    )

            # 5. 生成
            span = trace.start_span("generation")
            generation_start = time.time()
            if not sources:
                answer = "知识库中未找到相关信息"
                usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            else:
                result = self.generator.generate(
                    question, sources, history=history, summary=summary,
                )
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
                intent=intent,
            )

        except Exception as e:
            trace.status = "error"
            metrics.inc_counter("total_errors")
            raise
        finally:
            trace.finish()
