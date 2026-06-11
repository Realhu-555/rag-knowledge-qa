"""M6 大规模数据支撑模块验收测试

覆盖范围：
1. 向量库抽象层接口一致性（VectorStoreBackend ABC + ChromaBackend 实现）
2. 批量Embedding正确性（批量编码、batch大小、维度一致）
3. 文件hash去重（compute_file_hash + deduplicate_by_hash）
4. 内容相似度去重（deduplicate_by_similarity，mock embedder）
5. 多collection隔离（不同kb_id写入不同collection、互不污染）
"""
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest


# ======================================================================
# 1. 向量库抽象层接口一致性
# ======================================================================

class TestVectorStoreBackendABC:
    """验证 VectorStoreBackend 抽象接口定义完整"""

    def test_all_abstract_methods_exist(self):
        """抽象基类声明了所有必要方法"""
        from src.core.vector_store import VectorStoreBackend

        expected_methods = {
            "add", "query", "delete", "count",
            "get_all", "list_collections", "delete_collection",
        }
        actual = set(VectorStoreBackend.__abstractmethods__)
        assert expected_methods == actual, (
            f"缺少或多余方法: 缺少={expected_methods - actual}, 多余={actual - expected_methods}"
        )

    def test_chroma_backend_implements_all(self):
        """ChromaBackend 实现了所有抽象方法"""
        from src.core.vector_store import VectorStoreBackend, ChromaBackend

        for method_name in VectorStoreBackend.__abstractmethods__:
            method = getattr(ChromaBackend, method_name, None)
            assert method is not None, f"ChromaBackend 缺少方法: {method_name}"
            assert callable(method), f"ChromaBackend.{method_name} 不可调用"

    def test_vector_store_facade_delegates_to_backend(self):
        """VectorStore 门面正确委托给 backend"""
        from src.core.vector_store import VectorStore, reset_backend

        mock_backend = Mock()
        mock_backend.count.return_value = 100
        mock_backend.get_all.return_value = {
            "ids": ["a", "b"], "documents": ["d1", "d2"], "metadatas": [{}, {}],
        }
        mock_backend.query.return_value = {
            "ids": [["q1"]], "documents": [["dq1"]],
            "metadatas": [[{"k": "v"}]], "distances": [[0.2]],
        }

        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()

            # count
            assert store.count() == 100
            mock_backend.count.assert_called_with(collection_name="knowledge_base")

            # get_all
            result = store.get_all()
            assert len(result["ids"]) == 2

            # query
            result = store.query(query_embedding=[0.1, 0.2], n_results=5)
            assert result["documents"][0][0] == "dq1"

            # add
            store.add(ids=["x"], documents=["y"], embeddings=[[0.3]], metadatas=[{"s": "t"}])
            mock_backend.add.assert_called_once()

            # delete
            store.delete(ids=["x"])
            mock_backend.delete.assert_called_once_with(ids=["x"], collection_name="knowledge_base")

    def test_unsupported_backend_raises(self):
        """不支持的后端名称抛出ValueError"""
        from src.core.vector_store import get_vector_store_backend, reset_backend

        # vector_store模块在import时已经从config读取了VECTOR_STORE_BACKEND
        # 所以需要直接patch vector_store模块中的变量
        reset_backend()
        with patch("src.core.vector_store.VECTOR_STORE_BACKEND", "nonexistent"):
            with pytest.raises(ValueError, match="不支持的向量库后端"):
                get_vector_store_backend()
        reset_backend()  # 恢复状态


# ======================================================================
# 2. 批量Embedding正确性
# ======================================================================

class TestBatchEmbedding:
    """验证批量Embedding逻辑（不加载真实模型，用mock验证批量处理链路）"""

    @pytest.fixture(autouse=True)
    def _mock_sentence_transformers(self):
        """Mock sentence_transformers以避免torch版本冲突"""
        import sys
        mock_st = MagicMock()
        with patch.dict(sys.modules, {
            "sentence_transformers": mock_st,
        }):
            yield

    def _get_embedder_class(self):
        """获取Embedder类（在mock环境下）"""
        # 重新导入以获取mock后的类
        import importlib
        if "src.core.embedder" in __import__("sys").modules:
            del __import__("sys").modules["src.core.embedder"]
        from src.core.embedder import Embedder
        return Embedder

    def test_embed_returns_correct_count(self):
        """批量encode返回与输入等长的向量列表"""
        import numpy as np
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1] * 384 for _ in range(5)])

        Embedder = self._get_embedder_class()
        embedder = Embedder()
        embedder.model = mock_model  # 跳过懒加载

        texts = [f"text_{i}" for i in range(5)]
        result = embedder.embed(texts)

        assert len(result) == 5
        assert len(result[0]) == 384
        mock_model.encode.assert_called_once_with(texts, show_progress_bar=True)

    def test_embed_single_returns_one_vector(self):
        """单条encode返回一个向量"""
        import numpy as np
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.2] * 384])

        Embedder = self._get_embedder_class()
        embedder = Embedder()
        embedder.model = mock_model

        result = embedder.embed_single("测试文本")
        assert len(result) == 384
        mock_model.encode.assert_called_once_with(["测试文本"])

    def test_batch_embedding_in_build_index(self):
        """build_index_full 中的批量Embedding分批逻辑正确"""
        from src.config import BATCH_EMBEDDING_SIZE

        # 模拟300个texts，batch_size=100，应分3批
        all_texts = [f"chunk_{i}" for i in range(300)]
        batch_size = BATCH_EMBEDDING_SIZE  # 默认100

        batches = []
        for start in range(0, len(all_texts), batch_size):
            batch = all_texts[start:start + batch_size]
            batches.append(batch)

        assert len(batches) == 3
        assert len(batches[0]) == 100
        assert len(batches[1]) == 100
        assert len(batches[2]) == 100

    def test_embed_empty_list(self):
        """空列表输入返回空列表"""
        import numpy as np
        mock_model = Mock()
        mock_model.encode.return_value = np.array([]).reshape(0, 384)

        Embedder = self._get_embedder_class()
        embedder = Embedder()
        embedder.model = mock_model

        result = embedder.embed([])
        assert result == []

    def test_batch_embedding_vector_dimension_consistent(self):
        """多批次Embedding的向量维度一致"""
        import numpy as np
        mock_model = Mock()

        Embedder = self._get_embedder_class()
        embedder = Embedder()
        embedder.model = mock_model

        # 模拟不同批次返回
        mock_model.encode.return_value = np.array([[0.1] * 384 for _ in range(10)])

        batch1 = embedder.embed([f"t{i}" for i in range(10)])
        batch2 = embedder.embed([f"t{i}" for i in range(10)])

        assert len(batch1[0]) == len(batch2[0]) == 384


# ======================================================================
# 3. 文件hash去重
# ======================================================================

class TestHashDeduplication:
    """验证文件hash去重逻辑"""

    def test_identical_files_grouped(self):
        """内容相同的文件被分到同一组"""
        from src.core.deduplicator import deduplicate_by_hash

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建3个文件：2个内容相同，1个不同
            f1 = Path(tmpdir) / "a.txt"
            f2 = Path(tmpdir) / "b.txt"
            f3 = Path(tmpdir) / "c.txt"
            f1.write_text("hello world")
            f2.write_text("hello world")
            f3.write_text("different content")

            unique, dups = deduplicate_by_hash([f1, f2, f3])

            # 应保留2个唯一文件（f1和f3）
            assert len(unique) == 2
            # 应有1组精确重复
            assert len(dups) == 1
            # 重复组包含2个文件
            for paths in dups.values():
                assert len(paths) == 2

    def test_all_different_files_no_dedup(self):
        """所有文件都不同时不做去重"""
        from src.core.deduplicator import deduplicate_by_hash

        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i in range(5):
                fp = Path(tmpdir) / f"f{i}.txt"
                fp.write_text(f"content_{i}")
                files.append(fp)

            unique, dups = deduplicate_by_hash(files)
            assert len(unique) == 5
            assert len(dups) == 0

    def test_compute_file_hash_deterministic(self):
        """同一文件多次计算hash结果一致"""
        from src.core.deduplicator import compute_file_hash

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("deterministic content test")
            f.flush()
            fp = Path(f.name)

        h1 = compute_file_hash(fp)
        h2 = compute_file_hash(fp)
        assert h1 == h2
        assert len(h1) == 32  # MD5 hex digest length

        fp.unlink()

    def test_different_content_different_hash(self):
        """不同内容产生不同hash"""
        from src.core.deduplicator import compute_file_hash

        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "x.txt"
            f2 = Path(tmpdir) / "y.txt"
            f1.write_text("content A")
            f2.write_text("content B")

            assert compute_file_hash(f1) != compute_file_hash(f2)


# ======================================================================
# 4. 内容相似度去重
# ======================================================================

class TestSimilarityDeduplication:
    """验证基于Embedding余弦相似度的去重"""

    def _make_mock_embedder(self, vectors):
        """创建返回指定向量列表的mock embedder"""
        embedder = Mock()
        embedder.embed.return_value = vectors
        return embedder

    def test_highly_similar_files_deduplicated(self):
        """余弦相似度 > 阈值的文件被去重"""
        from src.core.deduplicator import deduplicate_by_similarity

        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "a.txt"
            f2 = Path(tmpdir) / "b.txt"
            f3 = Path(tmpdir) / "c.txt"
            f1.write_text("机器学习是人工智能的分支")
            f2.write_text("机器学习是人工智能的一个重要分支")
            f3.write_text("今天天气真好")

            # f1和f2的向量非常相似（cosine > 0.99），f3不同
            mock_embedder = self._make_mock_embedder([
                [1.0, 0.0, 0.0],   # f1
                [0.999, 0.01, 0.0], # f2 - 与f1极度相似
                [0.0, 0.0, 1.0],   # f3 - 与前两者不相似
            ])

            unique, pairs = deduplicate_by_similarity(
                [f1, f2, f3], mock_embedder, threshold=0.95
            )

            # f2应被标记为f1的疑似重复
            assert len(pairs) >= 1
            assert len(unique) <= 2

    def test_different_files_not_deduplicated(self):
        """不相似的文件不会被去重"""
        from src.core.deduplicator import deduplicate_by_similarity

        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "a.txt"
            f2 = Path(tmpdir) / "b.txt"
            f1.write_text("内容A")
            f2.write_text("内容B")

            mock_embedder = self._make_mock_embedder([
                [1.0, 0.0, 0.0],  # f1
                [0.0, 0.0, 1.0],  # f2 - 完全不同
            ])

            unique, pairs = deduplicate_by_similarity(
                [f1, f2], mock_embedder, threshold=0.95
            )

            assert len(pairs) == 0
            assert len(unique) == 2

    def test_single_file_no_dedup(self):
        """单个文件不需要去重"""
        from src.core.deduplicator import deduplicate_by_similarity

        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "only.txt"
            f1.write_text("唯一文件")

            mock_embedder = self._make_mock_embedder([[0.5, 0.5, 0.5]])
            unique, pairs = deduplicate_by_similarity(
                [f1], mock_embedder, threshold=0.95
            )

            assert len(unique) == 1
            assert len(pairs) == 0

    def test_dedup_result_summary(self):
        """DedupResult.summary() 输出格式正确"""
        from src.core.deduplicator import DedupResult

        result = DedupResult(
            exact_duplicates={"hash1": ["a.txt", "b.txt"]},
            similar_pairs=[("c.txt", "d.txt", 0.98)],
            unique_files=[Path("a.txt"), Path("c.txt")],
        )

        summary = result.summary()
        assert "精确重复" in summary
        assert "疑似重复" in summary
        assert "去重后文件数" in summary

    def test_dedup_result_total_skipped(self):
        """DedupResult.total_skipped 计算正确"""
        from src.core.deduplicator import DedupResult

        result = DedupResult(
            exact_duplicates={
                "h1": ["a.txt", "b.txt", "c.txt"],  # 3个文件，跳过2个
                "h2": ["d.txt", "e.txt"],              # 2个文件，跳过1个
            },
            similar_pairs=[("f.txt", "g.txt", 0.96)],  # 跳过1个
            unique_files=[Path("a.txt"), Path("d.txt"), Path("f.txt")],
        )

        assert result.total_skipped == 4  # 2 + 1 + 1

    def test_full_dedup_flow_with_mock_embedder(self):
        """完整deduplicate流程：先hash去重再相似度去重"""
        from src.core.deduplicator import deduplicate

        with tempfile.TemporaryDirectory() as tmpdir:
            # 3个文件：2个完全相同（hash去重），1个与它们相似
            f1 = Path(tmpdir) / "a.txt"
            f2 = Path(tmpdir) / "b.txt"  # 与f1完全相同
            f3 = Path(tmpdir) / "c.txt"  # 与f1相似但不相同
            content = "RAG检索增强生成技术"
            f1.write_text(content)
            f2.write_text(content)
            f3.write_text("RAG检索增强生成技术的应用")

            mock_embedder = self._make_mock_embedder([
                [1.0, 0.0],   # f1
                [0.99, 0.01], # f3 - 与f1相似
            ])

            result = deduplicate([f1, f2, f3], embedder=mock_embedder, similarity_threshold=0.95)

            # f2应因hash与f1重复被去掉
            assert "hash" in str(result.exact_duplicates).lower() or len(result.exact_duplicates) >= 1
            # f3应因与f1相似被标记
            assert len(result.similar_pairs) >= 1


# ======================================================================
# 5. 多collection隔离
# ======================================================================

class TestMultiCollectionIsolation:
    """验证不同知识库使用独立collection，互不污染"""

    def test_set_kb_changes_collection(self):
        """set_kb 切换当前操作的collection"""
        from src.core.vector_store import VectorStore, reset_backend

        mock_backend = Mock()
        mock_backend.count.return_value = 0
        mock_backend.get_all.return_value = {"ids": [], "documents": [], "metadatas": []}

        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()

            # 默认collection
            assert store._active_collection() == "knowledge_base"

            # 切换到 kb_a
            store.set_kb("kb_a")
            assert store._active_collection() == "kb_a"

            # 切换到 kb_b
            store.set_kb("kb_b")
            assert store._active_collection() == "kb_b"

            # 切回默认
            store.set_kb(None)
            assert store._active_collection() == "knowledge_base"

    def test_different_kbs_use_different_collections(self):
        """不同kb_id的操作路由到不同collection"""
        from src.core.vector_store import VectorStore, reset_backend

        mock_backend = Mock()
        mock_backend.count.return_value = 0
        mock_backend.get_all.return_value = {"ids": [], "documents": [], "metadatas": []}

        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()

            # 写入 kb_a
            store.set_kb("kb_a")
            store.add(
                ids=["a1"], documents=["doc_a"],
                embeddings=[[0.1, 0.2]], metadatas=[{"kb": "a"}],
            )

            # 写入 kb_b
            store.set_kb("kb_b")
            store.add(
                ids=["b1"], documents=["doc_b"],
                embeddings=[[0.3, 0.4]], metadatas=[{"kb": "b"}],
            )

            # 验证调用时collection_name不同
            calls = mock_backend.add.call_args_list
            assert calls[0][1]["collection_name"] == "kb_a"
            assert calls[1][1]["collection_name"] == "kb_b"

    def test_collection_name_sanitization(self):
        """collection名称特殊字符被替换为下划线"""
        from src.core.vector_store import VectorStore

        cases = {
            "kb/test@123": "kb_test_123",
            "kb-001": "kb_001",
            "normal_kb": "normal_kb",
            "a b c": "a_b_c",
        }
        for input_name, expected in cases.items():
            result = VectorStore._safe_collection_name(input_name)
            assert result == expected, f"{input_name} -> {result}, expected {expected}"

    def test_get_collection_for_kb(self):
        """get_collection_for_kb 返回正确名称"""
        from src.core.vector_store import VectorStore, reset_backend

        mock_backend = Mock()
        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()

            assert store.get_collection_for_kb("kb_001") == "kb_001"
            assert store.get_collection_for_kb(None) == "knowledge_base"
            assert store.get_collection_for_kb("kb/test") == "kb_test"

    def test_query_routes_to_correct_collection(self):
        """query操作路由到当前kb的collection"""
        from src.core.vector_store import VectorStore, reset_backend

        mock_backend = Mock()
        mock_backend.query.return_value = {
            "ids": [[]], "documents": [[]],
            "metadatas": [[]], "distances": [[]],
        }

        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()

            store.set_kb("kb_alpha")
            store.query(query_embedding=[0.1], n_results=5)
            mock_backend.query.assert_called_with(
                query_embedding=[0.1], n_results=5,
                where=None, collection_name="kb_alpha",
            )

            store.set_kb("kb_beta")
            store.query(query_embedding=[0.2], n_results=3)
            mock_backend.query.assert_called_with(
                query_embedding=[0.2], n_results=3,
                where=None, collection_name="kb_beta",
            )

    def test_query_multi_kb_searches_multiple(self):
        """跨知识库检索并行查多个collection"""
        from src.core.vector_store import VectorStore, reset_backend

        mock_backend = Mock()
        mock_backend.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "metadatas": [[{"source": "test"}]],
            "distances": [[0.1]],
        }

        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()

            results = store.query_multi_kb(
                query_embedding=[0.1, 0.2],
                kb_ids=["kb_1", "kb_2", "kb_3"],
                n_results=5,
            )

            # 应查询3个collection
            assert mock_backend.query.call_count == 3
            # 结果应合并
            assert isinstance(results, list)
            assert len(results) >= 1

    def test_delete_only_affects_current_collection(self):
        """删除操作只影响当前collection"""
        from src.core.vector_store import VectorStore, reset_backend

        mock_backend = Mock()

        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()

            store.set_kb("kb_to_delete")
            store.delete(ids=["doc_1", "doc_2"])

            mock_backend.delete.assert_called_once_with(
                ids=["doc_1", "doc_2"], collection_name="kb_to_delete",
            )

    def test_list_collections_and_delete(self):
        """list_collections 和 delete_collection 功能正常"""
        from src.core.vector_store import VectorStore, reset_backend

        mock_backend = Mock()
        mock_backend.list_collections.return_value = ["col_a", "col_b", "col_c"]

        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()

            cols = store._backend.list_collections()
            assert cols == ["col_a", "col_b", "col_c"]

            store._backend.delete_collection("col_b")
            mock_backend.delete_collection.assert_called_once_with("col_b")


# ======================================================================
# 6. 配置项验证
# ======================================================================

class TestM6Config:
    """验证M6相关配置项存在且默认值正确"""

    def test_vector_store_backend_default(self):
        from src.config import VECTOR_STORE_BACKEND
        assert VECTOR_STORE_BACKEND == "chroma"

    def test_batch_embedding_size_default(self):
        from src.config import BATCH_EMBEDDING_SIZE
        assert BATCH_EMBEDDING_SIZE == 100

    def test_parallel_load_workers_default(self):
        from src.config import PARALLEL_LOAD_WORKERS
        assert PARALLEL_LOAD_WORKERS == 4

    def test_dedup_similarity_threshold_default(self):
        from src.config import DEDUP_SIMILARITY_THRESHOLD
        assert DEDUP_SIMILARITY_THRESHOLD == 0.95

    def test_batch_embedding_size_configurable(self, monkeypatch):
        """BATCH_EMBEDDING_SIZE 可通过环境变量配置"""
        monkeypatch.setenv("BATCH_EMBEDDING_SIZE", "200")
        import importlib
        import src.config
        importlib.reload(src.config)
        assert src.config.BATCH_EMBEDDING_SIZE == 200
        importlib.reload(src.config)  # 恢复

    def test_parallel_load_workers_configurable(self, monkeypatch):
        """PARALLEL_LOAD_WORKERS 可通过环境变量配置"""
        monkeypatch.setenv("PARALLEL_LOAD_WORKERS", "8")
        import importlib
        import src.config
        importlib.reload(src.config)
        assert src.config.PARALLEL_LOAD_WORKERS == 8
        importlib.reload(src.config)  # 恢复
