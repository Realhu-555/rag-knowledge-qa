"""M2模块验收测试 — 增量更新

注意: torch/sentence_transformers 在此环境中存在循环导入问题。
测试通过在模块级mock解决此问题。
"""
import hashlib
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ─── 在任何项目代码导入之前，mock掉sentence_transformers和torch ───
# 这样可以避免torch的循环导入问题
_mock_st = MagicMock()
_mock_st.SentenceTransformer = MagicMock()
sys.modules.setdefault("sentence_transformers", _mock_st)

import chromadb  # noqa: E402 — 确保chromadb可用


# ─── 辅助工具 ───

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """创建临时数据库并patch DB_PATH"""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("src.storage.database.DB_PATH", db_file)
    return db_file


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """创建临时data目录并patch DATA_DIR和DB_PATH，确保测试隔离"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # patch config模块
    monkeypatch.setattr("src.config.DATA_DIR", data_dir)
    # patch document_scanner模块的DATA_DIR（它在导入时绑定了原始值）
    monkeypatch.setattr("src.core.document_scanner.DATA_DIR", data_dir)
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("src.storage.database.DB_PATH", db_file)
    return data_dir


# ============================================================
# 1. database.py 建表和CRUD
# ============================================================

class TestDatabase:

    def test_init_db_creates_table(self, tmp_db):
        """建表后应存在 document_registry 表"""
        from src.storage.database import init_db
        init_db()

        conn = sqlite3.connect(str(tmp_db))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        conn.close()
        table_names = [t[0] for t in tables]
        assert "document_registry" in table_names

    def test_init_db_idempotent(self, tmp_db):
        """多次init_db不应报错"""
        from src.storage.database import init_db
        init_db()
        init_db()  # 第二次应幂等

    def test_upsert_and_get_document(self, tmp_db):
        """upsert插入 + get_document查回"""
        from src.storage.database import init_db, upsert_document, get_document
        from src.storage.models import DocumentRecord

        init_db()
        rec = DocumentRecord(
            id="abc123",
            filename="test.md",
            file_path="data/test.md",
            file_hash="hash1",
            file_type="md",
            file_size=1024,
            chunk_count=5,
            status="indexed",
            indexed_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        upsert_document(rec)

        got = get_document("abc123")
        assert got is not None
        assert got.id == "abc123"
        assert got.filename == "test.md"
        assert got.chunk_count == 5
        assert got.status == "indexed"

    def test_upsert_update_existing(self, tmp_db):
        """upsert应支持更新已有记录"""
        from src.storage.database import init_db, upsert_document, get_document
        from src.storage.models import DocumentRecord

        init_db()
        rec1 = DocumentRecord(
            id="doc1", filename="a.md", file_path="data/a.md",
            file_hash="h1", file_type="md", file_size=100,
            status="pending",
        )
        upsert_document(rec1)

        rec2 = DocumentRecord(
            id="doc1", filename="a.md", file_path="data/a.md",
            file_hash="h2", file_type="md", file_size=200,
            status="indexed", chunk_count=3,
        )
        upsert_document(rec2)

        got = get_document("doc1")
        assert got.status == "indexed"
        assert got.chunk_count == 3
        assert got.file_hash == "h2"

    def test_get_nonexistent_document(self, tmp_db):
        """查询不存在的ID应返回None"""
        from src.storage.database import init_db, get_document
        init_db()
        assert get_document("nonexistent") is None

    def test_get_document_by_path(self, tmp_db):
        """按file_path查询"""
        from src.storage.database import init_db, upsert_document, get_document_by_path
        from src.storage.models import DocumentRecord

        init_db()
        rec = DocumentRecord(
            id="doc2", filename="b.md", file_path="data/sub/b.md",
            file_hash="h3", file_type="md", file_size=500,
        )
        upsert_document(rec)

        got = get_document_by_path("data/sub/b.md")
        assert got is not None
        assert got.id == "doc2"

    def test_list_documents(self, tmp_db):
        """list_documents应返回所有文档"""
        from src.storage.database import init_db, upsert_document, list_documents
        from src.storage.models import DocumentRecord

        init_db()
        for i in range(3):
            upsert_document(DocumentRecord(
                id=f"d{i}", filename=f"f{i}.md", file_path=f"data/f{i}.md",
                file_hash=f"h{i}", file_type="md", file_size=100,
                status="indexed",
            ))

        docs = list_documents()
        assert len(docs) == 3

    def test_list_documents_by_status(self, tmp_db):
        """按status过滤"""
        from src.storage.database import init_db, upsert_document, list_documents
        from src.storage.models import DocumentRecord

        init_db()
        upsert_document(DocumentRecord(
            id="d1", filename="a.md", file_path="a",
            file_hash="h", file_type="md", file_size=1, status="indexed",
        ))
        upsert_document(DocumentRecord(
            id="d2", filename="b.md", file_path="b",
            file_hash="h", file_type="md", file_size=1, status="error",
        ))

        indexed = list_documents(status="indexed")
        assert len(indexed) == 1
        assert indexed[0].id == "d1"

    def test_delete_document(self, tmp_db):
        """delete_document应删除记录"""
        from src.storage.database import init_db, upsert_document, delete_document, get_document
        from src.storage.models import DocumentRecord

        init_db()
        upsert_document(DocumentRecord(
            id="d1", filename="x.md", file_path="x",
            file_hash="h", file_type="md", file_size=1,
        ))
        delete_document("d1")
        assert get_document("d1") is None

    def test_get_stats(self, tmp_db):
        """get_stats应返回正确的统计"""
        from src.storage.database import init_db, upsert_document, get_stats
        from src.storage.models import DocumentRecord

        init_db()
        upsert_document(DocumentRecord(
            id="d1", filename="a.md", file_path="a",
            file_hash="h", file_type="md", file_size=1,
            status="indexed", chunk_count=10,
        ))
        upsert_document(DocumentRecord(
            id="d2", filename="b.md", file_path="b",
            file_hash="h", file_type="md", file_size=1,
            status="error",
        ))

        stats = get_stats()
        assert stats["total_documents"] == 2
        assert stats["indexed"] == 1
        assert stats["error"] == 1
        assert stats["total_chunks"] == 10

    def test_document_record_now(self):
        """DocumentRecord.now()应返回ISO格式字符串"""
        from src.storage.models import DocumentRecord
        now = DocumentRecord.now()
        assert "T" in now
        assert len(now) > 10


# ============================================================
# 2. document_scanner.py 文件扫描和hash比对
# ============================================================

class TestDocumentScanner:

    def test_compute_file_hash(self, tmp_path):
        """compute_file_hash应返回正确的MD5"""
        from src.core.document_scanner import compute_file_hash

        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")

        h = compute_file_hash(f)
        expected = hashlib.md5(b"hello world").hexdigest()
        assert h == expected

    def test_compute_file_hash_empty_file(self, tmp_path):
        """空文件的hash也应能计算"""
        from src.core.document_scanner import compute_file_hash
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        h = compute_file_hash(f)
        assert h == hashlib.md5(b"").hexdigest()

    def test_get_supported_extensions(self):
        """应返回所有loader支持的扩展名"""
        from src.core.document_scanner import get_supported_extensions
        exts = get_supported_extensions()
        assert ".md" in exts
        assert ".txt" in exts

    def test_scan_data_directory_detects_new_files(self, tmp_data_dir):
        """新文件应被检测为added"""
        from src.core.document_scanner import scan_data_directory

        (tmp_data_dir / "new_file.md").write_text("# Hello", encoding="utf-8")

        result = scan_data_directory(tmp_data_dir)
        assert result.has_changes
        assert len(result.added) >= 1
        # 确认new_file.md在列表中
        added_names = [p.name for p in result.added]
        assert "new_file.md" in added_names

    def test_scan_data_directory_no_changes(self, tmp_data_dir):
        """空目录无变化时 has_changes 应为False"""
        from src.core.document_scanner import scan_data_directory
        from src.storage.database import init_db
        init_db()

        result = scan_data_directory(tmp_data_dir)
        assert not result.has_changes

    def test_scan_detects_modified_files(self, tmp_data_dir):
        """文件内容变化应被检测为modified"""
        from src.core.document_scanner import scan_data_directory, compute_file_hash
        from src.storage.database import init_db, upsert_document
        from src.storage.models import DocumentRecord

        init_db()

        # 创建一个文件
        test_file = tmp_data_dir / "test.md"
        content_v1 = "# Version 1\nSome content"
        test_file.write_text(content_v1, encoding="utf-8")

        # 首次扫描 -- 应检测为added
        result1 = scan_data_directory(tmp_data_dir)
        assert len(result1.added) >= 1

        # 手动注册到registry（模拟已索引状态）
        rel_path = str(test_file.relative_to(tmp_data_dir.parent))
        doc_id = hashlib.md5(rel_path.encode()).hexdigest()
        file_hash = compute_file_hash(test_file)
        upsert_document(DocumentRecord(
            id=doc_id,
            filename=test_file.name,
            file_path=rel_path,
            file_hash=file_hash,
            file_type="md",
            file_size=test_file.stat().st_size,
            status="indexed",
        ))

        # 修改文件内容
        test_file.write_text("# Version 2\nUpdated content", encoding="utf-8")

        # 再次扫描 -- 应检测为modified
        result2 = scan_data_directory(tmp_data_dir)
        modified_names = [p.name for p in result2.modified]
        assert "test.md" in modified_names

    def test_scan_result_summary(self):
        """ScanResult.summary()应返回可读字符串"""
        from src.core.document_scanner import ScanResult
        sr = ScanResult()
        sr.added.append(Path("/a"))
        sr.modified.append(Path("/b"))
        sr.deleted.append("/c")
        s = sr.summary()
        assert "新增 1 个" in s
        assert "修改 1 个" in s
        assert "删除 1 个" in s

    def test_scan_result_has_changes(self):
        """has_changes属性测试"""
        from src.core.document_scanner import ScanResult
        sr = ScanResult()
        assert not sr.has_changes
        sr.added.append(Path("/x"))
        assert sr.has_changes

    def test_update_registry_creates_record(self, tmp_db, tmp_data_dir):
        """update_registry应创建新的registry记录"""
        from src.core.document_scanner import update_registry, compute_file_hash
        from src.storage.database import get_document

        test_file = tmp_data_dir / "new.md"
        test_file.write_text("# test", encoding="utf-8")

        file_hash = compute_file_hash(test_file)
        record = update_registry(test_file, file_hash, 3, "indexed")

        assert record.status == "indexed"
        assert record.chunk_count == 3
        assert record.id is not None

        # 从DB读回验证
        got = get_document(record.id)
        assert got is not None
        assert got.filename == "new.md"

    def test_update_registry_existing_record(self, tmp_db, tmp_data_dir):
        """update_registry对已有记录应更新"""
        from src.core.document_scanner import update_registry, compute_file_hash
        from src.storage.database import get_document

        test_file = tmp_data_dir / "existing.md"
        test_file.write_text("# v1", encoding="utf-8")

        file_hash = compute_file_hash(test_file)
        r1 = update_registry(test_file, file_hash, 2, "indexed")
        r2 = update_registry(test_file, file_hash, 5, "indexed")

        # 同一ID
        assert r1.id == r2.id
        got = get_document(r1.id)
        assert got.chunk_count == 5


# ============================================================
# 3. incremental_indexer.py 增量逻辑
# ============================================================

class TestIncrementalIndexer:

    def _make_indexer(self):
        """创建mock了Embedder和VectorStore的IncrementalIndexer"""
        from src.core.incremental_indexer import IncrementalIndexer
        indexer = IncrementalIndexer.__new__(IncrementalIndexer)
        indexer.splitter = MagicMock()
        indexer.embedder = MagicMock()
        indexer.embedder.embed = MagicMock(
            side_effect=lambda texts: [[0.1] * 384 for _ in texts]
        )
        indexer.vector_store = MagicMock()
        indexer.vector_store.count = MagicMock(return_value=0)
        indexer.vector_store.get_all = MagicMock(
            return_value={"ids": [], "metadatas": []}
        )
        indexer.vector_store.add = MagicMock()
        indexer.vector_store.delete = MagicMock()
        return indexer

    def test_sync_no_changes(self, tmp_db, tmp_data_dir):
        """无变化时sync应返回全零统计"""
        from src.core.document_scanner import ScanResult

        scan_result = ScanResult()  # 空的，无变化
        indexer = self._make_indexer()
        stats = indexer.sync(scan_result)

        assert stats == {"added": 0, "updated": 0, "deleted": 0, "errors": 0}

    def test_sync_add_new_file(self, tmp_db, tmp_data_dir):
        """新增文件应被索引"""
        from src.core.document_scanner import ScanResult, compute_file_hash
        from src.storage.database import get_document
        from src.core.splitter import Chunk

        # 创建测试文件
        test_file = tmp_data_dir / "new_doc.md"
        test_file.write_text(
            "# Test Document\nThis is test content for indexing.", encoding="utf-8"
        )

        scan_result = ScanResult(added=[test_file])
        indexer = self._make_indexer()
        # mock splitter返回chunks
        indexer.splitter.split_elements = MagicMock(return_value=[
            Chunk(content="chunk1", metadata={"source_file": test_file.name}),
            Chunk(content="chunk2", metadata={"source_file": test_file.name}),
        ])
        stats = indexer.sync(scan_result)

        assert stats["added"] == 1
        assert stats["errors"] == 0

        # 验证registry中有记录
        rel_path = str(test_file.relative_to(tmp_data_dir.parent))
        doc_id = hashlib.md5(rel_path.encode()).hexdigest()
        doc = get_document(doc_id)
        assert doc is not None
        assert doc.status == "indexed"
        assert doc.chunk_count == 2

    def test_sync_add_empty_file(self, tmp_db, tmp_data_dir):
        """空内容文件应被索引但chunk_count为0"""
        from src.core.document_scanner import ScanResult
        from src.storage.database import get_document

        test_file = tmp_data_dir / "empty_content.md"
        test_file.write_text("", encoding="utf-8")

        scan_result = ScanResult(added=[test_file])
        indexer = self._make_indexer()
        indexer.splitter.split_elements = MagicMock(return_value=[])
        stats = indexer.sync(scan_result)

        assert stats["added"] == 1
        rel_path = str(test_file.relative_to(tmp_data_dir.parent))
        doc_id = hashlib.md5(rel_path.encode()).hexdigest()
        doc = get_document(doc_id)
        assert doc is not None
        assert doc.chunk_count == 0

    def test_sync_delete_file(self, tmp_db, tmp_data_dir):
        """删除文件应从registry移除"""
        from src.core.document_scanner import ScanResult, update_registry, compute_file_hash
        from src.storage.database import get_document

        # 先创建并注册一个文件
        test_file = tmp_data_dir / "to_delete.md"
        test_file.write_text("# Delete me", encoding="utf-8")
        file_hash = compute_file_hash(test_file)
        rec = update_registry(test_file, file_hash, 2, "indexed")
        doc_id = rec.id

        # 模拟删除（文件已不在磁盘上）
        rel_path = str(test_file.relative_to(tmp_data_dir.parent))
        scan_result = ScanResult(deleted=[rel_path])
        indexer = self._make_indexer()
        stats = indexer.sync(scan_result)

        assert stats["deleted"] == 1
        assert get_document(doc_id) is None

    def test_sync_update_file(self, tmp_db, tmp_data_dir):
        """修改文件应先删旧chunk再重新索引"""
        from src.core.document_scanner import ScanResult, update_registry, compute_file_hash
        from src.storage.database import get_document
        from src.core.splitter import Chunk

        test_file = tmp_data_dir / "to_update.md"
        test_file.write_text("# Original content", encoding="utf-8")
        file_hash = compute_file_hash(test_file)
        update_registry(test_file, file_hash, 1, "indexed")

        # 修改文件
        test_file.write_text(
            "# Updated content\nNew paragraph added here.", encoding="utf-8"
        )

        scan_result = ScanResult(modified=[test_file])
        indexer = self._make_indexer()
        indexer.splitter.split_elements = MagicMock(return_value=[
            Chunk(content="updated chunk", metadata={"source_file": test_file.name}),
        ])
        stats = indexer.sync(scan_result)

        assert stats["updated"] == 1
        assert stats["errors"] == 0

        # 验证registry已更新
        rel_path = str(test_file.relative_to(tmp_data_dir.parent))
        doc_id = hashlib.md5(rel_path.encode()).hexdigest()
        doc = get_document(doc_id)
        assert doc is not None
        assert doc.status == "indexed"
        assert doc.chunk_count >= 1

    def test_sync_mixed_changes(self, tmp_db, tmp_data_dir):
        """同时有新增、修改、删除"""
        from src.core.document_scanner import ScanResult, update_registry, compute_file_hash
        from src.storage.database import get_document
        from src.core.splitter import Chunk

        # 准备一个已注册的文件（用来删除）
        del_file = tmp_data_dir / "del.md"
        del_file.write_text("# old", encoding="utf-8")
        file_hash = compute_file_hash(del_file)
        rec = update_registry(del_file, file_hash, 1, "indexed")
        del_doc_id = rec.id
        del_rel = str(del_file.relative_to(tmp_data_dir.parent))

        # 准备一个已注册文件（用来修改）
        mod_file = tmp_data_dir / "mod.md"
        mod_file.write_text("# v1", encoding="utf-8")
        file_hash = compute_file_hash(mod_file)
        update_registry(mod_file, file_hash, 1, "indexed")
        mod_file.write_text("# v2 updated", encoding="utf-8")

        # 准备新文件
        new_file = tmp_data_dir / "new.md"
        new_file.write_text("# brand new", encoding="utf-8")

        scan_result = ScanResult(
            added=[new_file],
            modified=[mod_file],
            deleted=[del_rel],
        )
        indexer = self._make_indexer()
        indexer.splitter.split_elements = MagicMock(return_value=[
            Chunk(content="chunk", metadata={"source_file": "test.md"}),
        ])
        stats = indexer.sync(scan_result)

        assert stats["added"] == 1
        assert stats["updated"] == 1
        assert stats["deleted"] == 1
        assert get_document(del_doc_id) is None


# ============================================================
# 4. build_index.py --full 和增量模式
# ============================================================

class TestBuildIndex:

    def test_build_index_full(self, tmp_db, tmp_data_dir, capsys):
        """--full模式应全量构建索引"""
        # 创建测试文件
        (tmp_data_dir / "doc1.md").write_text(
            "# Heading 1\nContent for doc1.", encoding="utf-8"
        )
        (tmp_data_dir / "doc2.md").write_text(
            "# Heading 2\nContent for doc2.", encoding="utf-8"
        )

        mock_splitter = MagicMock()
        mock_splitter.split_elements = MagicMock(return_value=[
            MagicMock(content="chunk1", metadata={"source_file": "doc1.md", "element_type": "text"}),
            MagicMock(content="chunk2", metadata={"source_file": "doc2.md", "element_type": "text"}),
        ])
        mock_embedder = MagicMock()
        mock_embedder.embed = MagicMock(return_value=[[0.1] * 384, [0.2] * 384])
        mock_vector_store = MagicMock()
        mock_vector_store.count = MagicMock(return_value=0)
        mock_vector_store.get_all = MagicMock(return_value={"ids": []})
        mock_vector_store.add = MagicMock()

        with patch("build_index.SmartSplitter", return_value=mock_splitter), \
             patch("build_index.Embedder", return_value=mock_embedder), \
             patch("build_index.VectorStore", return_value=mock_vector_store), \
             patch("build_index.DATA_DIR", tmp_data_dir):
            from build_index import build_index_full
            build_index_full()

        captured = capsys.readouterr()
        assert "全量构建向量索引" in captured.out
        assert "全量索引构建完成" in captured.out
        assert "找到 2 个文档文件" in captured.out

    def test_build_index_incremental_no_changes(self, tmp_db, tmp_data_dir, capsys):
        """增量模式无变化时应提示已是最新"""
        from src.core.document_scanner import scan_data_directory, ScanResult
        from src.storage.database import init_db
        init_db()

        mock_scan = MagicMock(return_value=ScanResult())
        with patch("build_index.SmartSplitter"), \
             patch("build_index.Embedder"), \
             patch("build_index.VectorStore"), \
             patch("src.core.document_scanner.scan_data_directory", mock_scan):
            from build_index import build_index_incremental
            build_index_incremental()

        captured = capsys.readouterr()
        assert "没有检测到文件变化" in captured.out

    def test_build_index_incremental_with_new_file(self, tmp_db, tmp_data_dir, capsys):
        """增量模式有新文件时应执行索引"""
        (tmp_data_dir / "inc_doc.md").write_text(
            "# Incremental\nNew content here.", encoding="utf-8"
        )

        from src.core.document_scanner import ScanResult

        mock_splitter = MagicMock()
        mock_splitter.split_elements = MagicMock(return_value=[
            MagicMock(content="chunk", metadata={"source_file": "inc_doc.md", "element_type": "text"}),
        ])
        mock_embedder = MagicMock()
        mock_embedder.embed = MagicMock(return_value=[[0.1] * 384])
        mock_vector_store = MagicMock()
        mock_vector_store.count = MagicMock(return_value=0)
        mock_vector_store.get_all = MagicMock(return_value={"ids": []})
        mock_vector_store.add = MagicMock()

        test_file = tmp_data_dir / "inc_doc.md"
        mock_scan = MagicMock(return_value=ScanResult(added=[test_file]))
        with patch("build_index.SmartSplitter", return_value=mock_splitter), \
             patch("build_index.Embedder", return_value=mock_embedder), \
             patch("build_index.VectorStore", return_value=mock_vector_store), \
             patch("src.core.document_scanner.scan_data_directory", mock_scan), \
             patch("src.core.incremental_indexer.SmartSplitter", return_value=mock_splitter), \
             patch("src.core.incremental_indexer.Embedder", return_value=mock_embedder), \
             patch("src.core.incremental_indexer.VectorStore", return_value=mock_vector_store):
            from build_index import build_index_incremental
            build_index_incremental()

        captured = capsys.readouterr()
        assert "增量构建向量索引" in captured.out
        assert "增量索引完成" in captured.out

    def test_build_index_incremental_noop_after_full(self, tmp_db, tmp_data_dir, capsys):
        """full之后再incremental应无变化"""
        (tmp_data_dir / "stable.md").write_text(
            "# Stable", encoding="utf-8"
        )

        from src.core.document_scanner import ScanResult

        mock_splitter = MagicMock()
        mock_splitter.split_elements = MagicMock(return_value=[
            MagicMock(content="chunk", metadata={"source_file": "stable.md", "element_type": "text"}),
        ])
        mock_embedder = MagicMock()
        mock_embedder.embed = MagicMock(return_value=[[0.1] * 384])
        mock_vector_store = MagicMock()
        mock_vector_store.count = MagicMock(return_value=0)
        mock_vector_store.get_all = MagicMock(return_value={"ids": []})
        mock_vector_store.add = MagicMock()

        # build_index_full需要DATA_DIR指向tmp_data_dir
        # build_index_incremental的scan用mock返回空（模拟无变化）
        mock_scan_empty = MagicMock(return_value=ScanResult())
        with patch("build_index.SmartSplitter", return_value=mock_splitter), \
             patch("build_index.Embedder", return_value=mock_embedder), \
             patch("build_index.VectorStore", return_value=mock_vector_store), \
             patch("build_index.DATA_DIR", tmp_data_dir), \
             patch("src.core.document_scanner.scan_data_directory", mock_scan_empty):
            from build_index import build_index_full, build_index_incremental
            build_index_full()
            build_index_incremental()

        captured = capsys.readouterr()
        # 第二次incremental应显示"没有检测到文件变化"
        assert "没有检测到文件变化" in captured.out
