"""文档去重模块 — 文件hash去重 + 内容相似度去重

索引前检测重复文档，避免重复索引。
- 文件hash去重：MD5完全相同的文件不重复索引
- 内容相似度去重：Embedding余弦相似度 > 阈值 标记为疑似重复
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DedupResult:
    """去重检测结果"""
    exact_duplicates: dict[str, list[str]] = field(default_factory=dict)
    # hash -> [file_path, ...]，完全相同的文件
    similar_pairs: list[tuple[str, str, float]] = field(default_factory=list)
    # (file_a, file_b, similarity) 疑似重复对
    unique_files: list[Path] = field(default_factory=list)
    # 去重后保留的唯一文件

    @property
    def total_skipped(self) -> int:
        """被跳过的重复文件数"""
        count = 0
        for paths in self.exact_duplicates.values():
            count += len(paths) - 1  # 保留第一个，跳过其余
        count += len(self.similar_pairs)
        return count

    def summary(self) -> str:
        return (
            f"精确重复: {len(self.exact_duplicates)} 组, "
            f"疑似重复: {len(self.similar_pairs)} 对, "
            f"去重后文件数: {len(self.unique_files)}, "
            f"跳过: {self.total_skipped} 个"
        )


def compute_file_hash(file_path: Path) -> str:
    """计算文件MD5 hash"""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def deduplicate_by_hash(files: list[Path]) -> tuple[list[Path], dict[str, list[str]]]:
    """按文件hash去重

    Args:
        files: 待检测的文件列表

    Returns:
        (去重后的文件列表, hash重复映射表)
    """
    hash_map: dict[str, list[Path]] = {}
    for fp in files:
        h = compute_file_hash(fp)
        hash_map.setdefault(h, []).append(fp)

    unique: list[Path] = []
    duplicates: dict[str, list[str]] = {}
    for h, group in hash_map.items():
        # 保留第一个文件
        unique.append(group[0])
        if len(group) > 1:
            duplicates[h] = [str(p) for p in group]

    return unique, duplicates


def deduplicate_by_similarity(
    files: list[Path],
    embedder,
    threshold: float = 0.95,
    max_comparison: int = 500,
) -> tuple[list[Path], list[tuple[str, str, float]]]:
    """按内容Embedding余弦相似度去重

    对每个文件计算全文Embedding，两两比较余弦相似度。
    相似度 > threshold 的标记为疑似重复。

    Args:
        files: 待检测文件列表（已经过hash去重）
        embedder: Embedder实例
        threshold: 相似度阈值（0-1）
        max_comparison: 最大比较文件数（避免O(n^2)过慢）

    Returns:
        (保留的唯一文件列表, 疑似重复对列表)
    """
    if len(files) <= 1:
        return files, []

    sample_files = files[:max_comparison]

    # 读取每个文件的前2000字作为代表文本
    file_contents: list[str] = []
    for fp in sample_files:
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")[:2000]
            if not text.strip():
                text = fp.name  # 空文件用文件名代替
        except Exception:
            text = fp.name
        file_contents.append(text)

    # 批量计算Embedding
    embeddings = embedder.embed(file_contents)

    # 两两比较余弦相似度
    skip_indices: set[int] = set()
    similar_pairs: list[tuple[str, str, float]] = []

    for i in range(len(embeddings)):
        if i in skip_indices:
            continue
        for j in range(i + 1, len(embeddings)):
            if j in skip_indices:
                continue
            sim = _cosine_similarity(embeddings[i], embeddings[j])
            if sim > threshold:
                # 跳过后者，保留前者
                skip_indices.add(j)
                similar_pairs.append((str(sample_files[i]), str(sample_files[j]), round(sim, 4)))

    unique = [fp for idx, fp in enumerate(sample_files) if idx not in skip_indices]
    # 加上超出max_comparison范围的文件
    unique.extend(files[max_comparison:])

    return unique, similar_pairs


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def deduplicate(
    files: list[Path],
    embedder=None,
    similarity_threshold: float = 0.95,
) -> DedupResult:
    """完整去重流程

    Args:
        files: 待索引的文件列表
        embedder: Embedder实例（可选，不提供则只做hash去重）
        similarity_threshold: 相似度阈值

    Returns:
        DedupResult 去重结果
    """
    result = DedupResult()

    # 第一步：hash去重
    unique_by_hash, exact_dups = deduplicate_by_hash(files)
    result.exact_duplicates = exact_dups
    result.unique_files = unique_by_hash

    logger.info("Hash去重: %d -> %d 个文件", len(files), len(unique_by_hash))

    # 第二步：相似度去重（如果提供了embedder）
    if embedder is not None and len(unique_by_hash) > 1:
        unique_by_sim, similar_pairs = deduplicate_by_similarity(
            unique_by_hash, embedder, threshold=similarity_threshold
        )
        result.similar_pairs = similar_pairs
        result.unique_files = unique_by_sim

        logger.info("相似度去重: %d -> %d 个文件", len(unique_by_hash), len(unique_by_sim))

    return result


def print_dedup_report(result: DedupResult) -> None:
    """打印去重报告"""
    print("\n" + "=" * 50)
    print("文档去重报告")
    print("=" * 50)
    print(result.summary())

    if result.exact_duplicates:
        print("\n--- 精确重复文件 ---")
        for hash_val, paths in result.exact_duplicates.items():
            print(f"  Hash: {hash_val[:12]}...")
            for p in paths:
                print(f"    - {p}")
            print(f"  保留: {paths[0]}")

    if result.similar_pairs:
        print("\n--- 疑似重复文件 ---")
        for file_a, file_b, sim in result.similar_pairs:
            print(f"  相似度: {sim:.4f}")
            print(f"    A: {Path(file_a).name}")
            print(f"    B: {Path(file_b).name}")

    print("=" * 50)
