"""向量存储模块测试"""
import pytest
from unittest.mock import Mock, patch
from src.core.vector_store import VectorStore


class TestVectorStore:
    """VectorStore测试"""

    @patch('src.core.vector_store.chromadb')
    def test_add_documents(self, mock_chromadb):
        """添加文档"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        store = VectorStore()
        store.add(
            ids=["id1", "id2"],
            documents=["文档1", "文档2"],
            embeddings=[[0.1, 0.2], [0.3, 0.4]],
            metadatas=[{"source": "a"}, {"source": "b"}]
        )

        mock_collection.add.assert_called_once()

    @patch('src.core.vector_store.chromadb')
    def test_query_documents(self, mock_chromadb):
        """查询文档"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "documents": [["文档1"]],
            "metadatas": [[{"source": "a"}]],
            "distances": [[0.5]]
        }

        store = VectorStore()
        results = store.query(query_embedding=[0.1, 0.2], n_results=5)

        assert "documents" in results

    @patch('src.core.vector_store.chromadb')
    def test_delete_documents(self, mock_chromadb):
        """删除文档"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        store = VectorStore()
        store.delete(ids=["id1", "id2"])

        mock_collection.delete.assert_called_once_with(ids=["id1", "id2"])

    @patch('src.core.vector_store.chromadb')
    def test_count_documents(self, mock_chromadb):
        """统计文档数"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 42

        store = VectorStore()
        count = store.count()

        assert count == 42

    @patch('src.core.vector_store.chromadb')
    def test_lazy_initialization(self, mock_chromadb):
        """懒加载初始化"""
        store = VectorStore()
        assert store.client is None

        mock_client = Mock()
        mock_collection = Mock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 0

        store.count()
        assert store.client is not None
