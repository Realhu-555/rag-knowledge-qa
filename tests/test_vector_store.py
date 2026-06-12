"""向量存储模块测试"""
from unittest.mock import Mock, patch
from src.core.vector_store import VectorStore, ChromaBackend, reset_backend


class TestVectorStore:
    """VectorStore测试（通过mock backend）"""

    def _make_mock_backend(self):
        """创建mock后端"""
        mock_backend = Mock()
        mock_backend.count.return_value = 42
        mock_backend.get_all.return_value = {"ids": [], "documents": [], "metadatas": []}
        return mock_backend

    def test_add_documents(self):
        """添加文档"""
        mock_backend = self._make_mock_backend()
        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()
            store.add(
                ids=["id1", "id2"],
                documents=["文档1", "文档2"],
                embeddings=[[0.1, 0.2], [0.3, 0.4]],
                metadatas=[{"source": "a"}, {"source": "b"}],
            )
            mock_backend.add.assert_called_once()

    def test_query_documents(self):
        """查询文档"""
        mock_backend = self._make_mock_backend()
        mock_backend.query.return_value = {
            "documents": [["文档1"]],
            "metadatas": [[{"source": "a"}]],
            "distances": [[0.5]],
        }
        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()
            results = store.query(query_embedding=[0.1, 0.2], n_results=5)
            assert "documents" in results

    def test_delete_documents(self):
        """删除文档"""
        mock_backend = self._make_mock_backend()
        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()
            store.delete(ids=["id1", "id2"])
            mock_backend.delete.assert_called_once_with(
                ids=["id1", "id2"], collection_name="knowledge_base"
            )

    def test_count_documents(self):
        """统计文档数"""
        mock_backend = self._make_mock_backend()
        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()
            count = store.count()
            assert count == 42

    def test_kb_isolation(self):
        """知识库隔离 — 不同kb_id使用不同collection"""
        mock_backend = self._make_mock_backend()
        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()
            # 默认collection
            assert store._active_collection() == "knowledge_base"

            # 切换到特定kb
            store.set_kb("kb_001")
            assert store._active_collection() == "kb_001"

            # 切回默认
            store.set_kb(None)
            assert store._active_collection() == "knowledge_base"

    def test_collection_name_sanitization(self):
        """collection名称安全化"""
        safe = VectorStore._safe_collection_name("kb/test@123")
        assert safe == "kb_test_123"

    def test_get_collection_for_kb(self):
        """获取知识库collection名称"""
        mock_backend = self._make_mock_backend()
        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()
            assert store.get_collection_for_kb("kb_001") == "kb_001"
            assert store.get_collection_for_kb(None) == "knowledge_base"

    def test_query_multi_kb(self):
        """跨知识库检索"""
        mock_backend = self._make_mock_backend()
        mock_backend.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "metadatas": [[{"source": "a"}]],
            "distances": [[0.3]],
        }
        with patch("src.core.vector_store.get_vector_store_backend", return_value=mock_backend):
            reset_backend()
            store = VectorStore()
            results = store.query_multi_kb(
                query_embedding=[0.1, 0.2],
                kb_ids=["kb_001", "kb_002"],
                n_results=5,
            )
            assert isinstance(results, list)
            # 每个kb查一次
            assert mock_backend.query.call_count == 2


class TestChromaBackend:
    """ChromaBackend 集成测试（需要真实ChromaDB）"""

    def test_backend_interface(self):
        """验证ChromaBackend实现所有抽象方法"""
        from src.core.vector_store import VectorStoreBackend
        for method_name in VectorStoreBackend.__abstractmethods__:
            assert hasattr(ChromaBackend, method_name), f"Missing method: {method_name}"

    def test_backend_list_collections(self):
        """列出collections"""
        reset_backend()
        backend = ChromaBackend()
        cols = backend.list_collections()
        assert isinstance(cols, list)

    def test_backend_add_and_query(self):
        """添加后能查到"""
        reset_backend()
        backend = ChromaBackend()
        test_col = "test_m6_backend"

        # 清理可能存在的旧测试collection
        try:
            backend.delete_collection(test_col)
        except Exception:
            pass

        backend.add(
            ids=["test_id_1"],
            documents=["测试文档内容"],
            embeddings=[[0.1] * 384],
            metadatas=[{"source": "test"}],
            collection_name=test_col,
        )

        result = backend.query(
            query_embedding=[0.1] * 384,
            n_results=1,
            collection_name=test_col,
        )
        assert result["documents"][0][0] == "测试文档内容"

        # 清理
        backend.delete_collection(test_col)
