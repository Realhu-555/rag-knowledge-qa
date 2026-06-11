"""构建向量索引"""
import argparse
import hashlib
from pathlib import Path

from src.config import DATA_DIR
from src.core.loaders import LOADERS, get_loader_for_file
from src.core.splitter import SmartSplitter
from src.core.embedder import Embedder
from src.core.vector_store import VectorStore
from src.storage.database import init_db


def build_index_full():
    """全量模式：清空重建整个向量库"""
    print("=" * 50)
    print("全量构建向量索引")
    print("=" * 50)

    init_db()

    # 初始化组件
    splitter = SmartSplitter()
    embedder = Embedder()
    vector_store = VectorStore()

    # 1. 扫描所有支持的文件
    print("\n[1/4] 扫描文档文件...")

    # 支持的文件扩展名
    supported_extensions = set()
    for loader_cls in LOADERS:
        supported_extensions.update(loader_cls.supported_extensions())

    # 递归查找所有支持的文件
    all_files = []
    for ext in supported_extensions:
        all_files.extend(DATA_DIR.rglob(f"*{ext}"))

    # 去重并排序
    all_files = sorted(set(all_files))
    print(f"找到 {len(all_files)} 个文档文件")

    all_chunks = []
    file_stats = {}

    for file_path in all_files:
        print(f"  加载: {file_path.name}")

        # 获取合适的loader
        loader = get_loader_for_file(file_path)
        if loader is None:
            print(f"    跳过: 没有合适的loader")
            continue

        try:
            doc_elements = loader.load(file_path)

            # 使用SmartSplitter切分
            chunks = splitter.split_elements(doc_elements)
            all_chunks.extend(chunks)

            # 统计
            file_stats[file_path.name] = len(chunks)
            print(f"    切分为 {len(chunks)} 个chunk")

        except Exception as e:
            print(f"    加载失败: {e}")

    print(f"\n共切分为 {len(all_chunks)} 个chunk")

    if not all_chunks:
        print("没有找到任何文档内容，请检查data目录")
        return

    # 2. Embedding
    print("\n[2/4] 生成向量...")
    texts = [chunk.content for chunk in all_chunks]
    embeddings = embedder.embed(texts)
    print(f"向量维度: {len(embeddings[0])}")

    # 3. 存入ChromaDB
    print("\n[3/4] 存入向量库...")
    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(all_chunks):
        # 生成唯一ID
        source = chunk.metadata.get("source_file", "")
        chunk_id = hashlib.md5(f"{source}_{i}".encode()).hexdigest()
        ids.append(chunk_id)
        documents.append(chunk.content)
        metadatas.append(chunk.metadata)

    # 清空旧数据后重新添加
    try:
        old_count = vector_store.count()
        if old_count > 0:
            print(f"  清空旧数据: {old_count} 条")
            old_data = vector_store.get_all()
            vector_store.delete(ids=old_data["ids"])
    except Exception:
        pass

    vector_store.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
    print(f"  成功添加 {len(ids)} 条记录")

    # 4. 统计信息
    print("\n[4/4] 统计信息...")
    total_count = vector_store.count()
    print(f"向量库总记录数: {total_count}")

    print("\n各文件chunk数:")
    for file_name, count in sorted(file_stats.items()):
        print(f"  {file_name}: {count}")

    # 按元素类型统计
    type_stats = {}
    for chunk in all_chunks:
        elem_type = chunk.metadata.get("element_type", "unknown")
        type_stats[elem_type] = type_stats.get(elem_type, 0) + 1

    print("\n各元素类型chunk数:")
    for elem_type, count in sorted(type_stats.items()):
        print(f"  {elem_type}: {count}")

    print("\n" + "=" * 50)
    print("全量索引构建完成!")
    print("=" * 50)


def build_index_incremental():
    """增量模式：只处理变化的文件"""
    from src.core.document_scanner import scan_data_directory
    from src.core.incremental_indexer import IncrementalIndexer

    print("=" * 50)
    print("增量构建向量索引")
    print("=" * 50)

    init_db()

    # 1. 扫描变化
    print("\n[1/3] 扫描文件变化...")
    scan_result = scan_data_directory()
    print(f"  {scan_result.summary()}")

    if not scan_result.has_changes:
        print("\n没有检测到文件变化，索引已是最新")
        return

    # 2. 执行增量索引
    print("\n[2/3] 执行增量索引...")
    indexer = IncrementalIndexer()
    stats = indexer.sync(scan_result)

    # 3. 输出统计
    print("\n[3/3] 同步完成")
    print(f"  新增索引: {stats['added']} 个")
    print(f"  更新索引: {stats['updated']} 个")
    print(f"  删除索引: {stats['deleted']} 个")
    if stats["errors"] > 0:
        print(f"  错误: {stats['errors']} 个")

    print("\n" + "=" * 50)
    print("增量索引完成!")
    print("=" * 50)


def build_index():
    """构建向量索引（默认增量模式）"""
    parser = argparse.ArgumentParser(description="构建向量索引")
    parser.add_argument(
        "--full", action="store_true",
        help="全量模式：清空并重建整个向量库"
    )
    args = parser.parse_args()

    if args.full:
        build_index_full()
    else:
        build_index_incremental()


if __name__ == "__main__":
    build_index()
