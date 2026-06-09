"""构建向量索引"""
import hashlib
from pathlib import Path

from src.config import DATA_DIR
from src.core.loaders.markdown_loader import MarkdownLoader
from src.core.splitter import MarkdownSplitter
from src.core.embedder import Embedder
from src.core.vector_store import VectorStore


def build_index():
    """构建向量索引"""
    print("=" * 50)
    print("开始构建向量索引")
    print("=" * 50)

    # 初始化组件
    loader = MarkdownLoader()
    splitter = MarkdownSplitter()
    embedder = Embedder()
    vector_store = VectorStore()

    # 1. 加载所有md文件
    print("\n[1/4] 加载Markdown文件...")
    md_files = list(DATA_DIR.rglob("*.md"))
    print(f"找到 {len(md_files)} 个md文件")

    all_chunks = []
    for md_file in md_files:
        print(f"  加载: {md_file.name}")
        doc_elements = loader.load(md_file)

        for elem in doc_elements:
            chunks = splitter.split(elem.content, elem.metadata)
            all_chunks.extend(chunks)

    print(f"共切分为 {len(all_chunks)} 个chunk")

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
        chunk_id = hashlib.md5(f"{chunk.metadata.get('source', '')}_{i}".encode()).hexdigest()
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

    # 按文件统计
    file_stats = {}
    for chunk in all_chunks:
        source = chunk.metadata.get("source", "未知")
        file_stats[source] = file_stats.get(source, 0) + 1

    print("\n各文件chunk数:")
    for file_name, count in sorted(file_stats.items()):
        print(f"  {file_name}: {count}")

    print("\n" + "=" * 50)
    print("索引构建完成!")
    print("=" * 50)


if __name__ == "__main__":
    build_index()
