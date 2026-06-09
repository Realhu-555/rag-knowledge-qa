# RAG智能问答系统

基于个人知识库的智能问答API服务，支持多格式文档、查询理解、回答可追溯。

## 功能特性

- ✅ Markdown文档加载和智能切片（按标题+字数兜底）
- ✅ 本地Embedding模型（all-MiniLM-L6-v2）
- ✅ ChromaDB向量存储（持久化）
- ✅ 语义检索
- ✅ DeepSeek API生成（带引用标注[1][2][3]）
- ✅ Gradio Web界面（调试用）
- ✅ FastAPI REST API（生产用）

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
uv venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
uv pip install -r requirements.txt
```

### 2. 配置

复制 `.env.example` 为 `.env`，填入你的 DeepSeek API Key：

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

### 3. 构建索引

```bash
python build_index.py
```

### 4. 启动服务

**Gradio界面（调试用）：**
```bash
python app.py
# 访问 http://localhost:7860
```

**FastAPI服务：**
```bash
python main.py
# 访问 http://localhost:8080/docs 查看API文档
```

## 项目结构

```
rag-knowledge-qa/
├── src/
│   ├── core/           # RAG核心逻辑
│   │   ├── loaders/    # 文档加载器（插件化）
│   │   │   ├── base.py            # 统一接口
│   │   │   └── markdown_loader.py # Markdown加载器
│   │   ├── splitter.py       # 智能切片
│   │   ├── embedder.py       # Embedding
│   │   ├── vector_store.py   # ChromaDB封装
│   │   ├── retriever.py      # 检索引擎
│   │   ├── generator.py      # LLM生成
│   │   └── rag_engine.py     # RAG引擎（串联所有模块）
│   └── config.py       # 配置管理
├── data/               # 知识库文件（不修改）
├── chroma_db/          # ChromaDB持久化（git忽略）
├── build_index.py      # 构建索引脚本
├── app.py              # Gradio前端
├── main.py             # FastAPI入口
├── .env                # API密钥（不入git）
└── .env.example        # 配置示例
```

## 技术栈

- **语言**: Python 3.12+
- **包管理**: uv
- **Embedding**: sentence-transformers all-MiniLM-L6-v2（本地模型）
- **向量数据库**: ChromaDB（本地持久化）
- **LLM**: DeepSeek API（兼容OpenAI格式）
- **Web界面**: Gradio（调试用）
- **API服务**: FastAPI（生产用）

## 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| DEEPSEEK_API_KEY | - | DeepSeek API密钥（必填）|
| EMBEDDING_PROVIDER | local | Embedding提供者（local/api）|
| EMBEDDING_MODEL | all-MiniLM-L6-v2 | Embedding模型名 |
| CHUNK_SIZE | 500 | 切片大小（字符）|
| CHUNK_OVERLAP | 50 | 切片重叠（字符）|
| RETRIEVAL_TOP_K | 10 | 检索返回数量 |

## 使用示例

### Python代码调用

```python
from src.core.rag_engine import RAGEngine

engine = RAGEngine()
response = engine.query("什么是RAG？")

print(response.answer)
print(response.sources)
print(response.timing)
```

### API调用

```bash
curl -X POST "http://localhost:8080/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是RAG？"}'
```

## 开发说明

### 添加新的文档格式

1. 在 `src/core/loaders/` 下创建新的loader文件
2. 继承 `BaseLoader` 基类
3. 实现 `load()` 和 `supported_extensions()` 方法
4. 在 `__init__.py` 中导出

### 切换Embedding模型

修改 `.env` 中的 `EMBEDDING_PROVIDER` 和 `EMBEDDING_MODEL`，然后重新运行 `build_index.py`。

## License

MIT
