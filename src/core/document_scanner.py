"""文件变化检测 — 扫描data/目录并对比registry"""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from src.config import DATA_DIR
from src.core.loaders import LOADERS
from src.storage.database import init_db, list_documents, upsert_document
from src.storage.models import DocumentRecord


@dataclass
class ScanResult:
    """扫描结果"""
    added: list[Path] = field(default_factory=list)
    modified: list[Path] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)  # file_path列表

    @property
    def has_changes(self) -> bool:
        """是否有变化"""
        return bool(self.added or self.modified or self.deleted)

    def summary(self) -> str:
        """返回变化摘要"""
        return (
            f"新增 {len(self.added)} 个, "
            f"修改 {len(self.modified)} 个, "
            f"删除 {len(self.deleted)} 个"
        )


def compute_file_hash(file_path: Path) -> str:
    """计算文件MD5 hash"""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_supported_extensions() -> set[str]:
    """获取所有loader支持的文件扩展名"""
    extensions = set()
    for loader_cls in LOADERS:
        extensions.update(loader_cls.supported_extensions())
    return extensions


def scan_data_directory(data_dir: Path = DATA_DIR) -> ScanResult:
    """扫描data/目录，对比registry，找出变化

    Returns:
        ScanResult 包含新增/修改/删除的文件列表
    """
    init_db()

    # 收集磁盘上的所有支持文件
    supported_exts = get_supported_extensions()
    disk_files: dict[str, Path] = {}  # file_path -> Path

    for ext in supported_exts:
        for f in data_dir.rglob(f"*{ext}"):
            # 存储相对路径的字符串形式
            rel_path = str(f.relative_to(data_dir.parent))
            disk_files[rel_path] = f

    # 读取registry中已有的记录
    existing_records = list_documents()
    existing_paths: dict[str, DocumentRecord] = {
        r.file_path: r for r in existing_records
    }

    result = ScanResult()

    # 检测新增和修改
    for rel_path, disk_path in disk_files.items():
        current_hash = compute_file_hash(disk_path)

        if rel_path not in existing_paths:
            # 新文件
            result.added.append(disk_path)
        else:
            # 已有文件，检查hash是否变化
            existing = existing_paths[rel_path]
            if existing.file_hash != current_hash:
                result.modified.append(disk_path)

    # 检测删除
    for rel_path in existing_paths:
        if rel_path not in disk_files:
            result.deleted.append(rel_path)

    return result


def update_registry(
    file_path: Path,
    file_hash: str,
    chunk_count: int,
    status: str,
    error_message: str = "",
) -> DocumentRecord:
    """更新或创建registry记录

    Args:
        file_path: 文件绝对路径
        file_hash: 文件MD5
        chunk_count: 切片数量
        status: 状态 indexed/error
        error_message: 错误信息

    Returns:
        更新后的DocumentRecord
    """
    from src.config import DATA_DIR

    init_db()
    rel_path = str(file_path.relative_to(DATA_DIR.parent))
    doc_id = hashlib.md5(rel_path.encode()).hexdigest()
    stat = file_path.stat()
    now = DocumentRecord.now()

    # 判断是否已有记录
    existing = get_document_by_path_ref(doc_id, rel_path)

    record = DocumentRecord(
        id=doc_id,
        filename=file_path.name,
        file_path=rel_path,
        file_hash=file_hash,
        file_type=file_path.suffix.lstrip("."),
        file_size=stat.st_size,
        chunk_count=chunk_count,
        status=status,
        indexed_at=existing.indexed_at if existing and status == "indexed" else (now if status == "indexed" else ""),
        updated_at=now,
        error_message=error_message,
    )
    upsert_document(record)
    return record


def get_document_by_path_ref(doc_id: str, file_path: str) -> DocumentRecord | None:
    """通过ID或路径获取文档记录（内部辅助）"""
    from src.storage.database import get_document, get_document_by_path
    doc = get_document(doc_id)
    if doc:
        return doc
    return get_document_by_path(file_path)
