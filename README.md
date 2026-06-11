# RAG 智能问答系统

企业级知识库问答助手。用户提问后，系统从知识库检索相关文档片段，基于检索结果生成带引用标注的回答。

## 功能特性

- **多格式文档处理** — 支持 Markdown / TXT / DOCX / PDF / XLSX / 图片，Loader 插件化
- **智能切片** — 按标题切分，表格/图片整体保留，短 section 自动合并
- **混合检索** — 向量检索 + BM25 关键词检索，RRF 融合排序
- **查询理解** — 查询扩展、HyDE、意图分类
- **多轮对话** — SessionManager 管理会话历史，支持上下文追问
- **引用可追溯** — 回答中标注来源（文件名 + 章节名）
- **生产级能力** — JWT 认证、限流、结构化日志、指标监控、链路追踪、告警
- **自动评测** — 30 条测试用例，语义相似度评分，定时评测

## 技术栈

| 组件 | 技术 |
|------|------|
| LLM | DeepSeek API（兼容 OpenAI 格式） |
| Embedding | sentence-transformers all-MiniLM-L6-v2 |
| 向量数据库 | ChromaDB（本地持久化） |
| 关键词检索 | rank_bm25 + jieba 中文分词 |
| 前端 | Vue 3 + Vite + TypeScript + Element Plus |
| API 服务 | FastAPI + uvicorn + WebSocket |
| 数据库 | SQLite（API Key、会话、日志） |

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/)（Python 包管理）

### 安装

```bash
# 克隆仓库
git clone https://github.com/HuZhenhu/rag-knowledge-qa.git
cd rag-knowledge-qa

# 创建虚拟环境并安装依赖
uv venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# 配置 API 密钥
cp .env.example .env
# 编辑 .env 填入 DeepSeek API Key
```

### 构建索引

```bash
python build_index.py
# 全量重建：python build_index.py --full
```

### 启动服务

```bash
# 启动后端 API（http://localhost:8080）
python main.py

# 启动前端开发服务器（http://localhost:5173）
cd frontend && npm install && npm run dev
```

### API 调用

```bash
# 问答
curl -X POST http://localhost:8080/api/v1/query \
  -H "Authorization: Bearer sk-rag-dev-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是RAG", "top_k": 5}'

# 上传文档
curl -X POST http://localhost:8080/api/v1/documents/upload \
  -H "Authorization: Bearer sk-rag-dev-key-12345" \
  -F "file=@your_doc.pdf" -F "kb_id=default"

# 健康检查
curl http://localhost:8080/health \
  -H "Authorization: Bearer sk-rag-dev-key-12345"
```

## 项目结构

```
rag-knowledge-qa/
├── src/
│   ├── api/               # FastAPI 接口层（路由、鉴权、限流）
│   ├── core/              # RAG 核心逻辑
│   │   ├── loaders/       # 文档加载器（md/txt/docx/pdf/图片）
│   │   ├── splitter.py    # 智能切片
│   │   ├── embedder.py    # Embedding
│   │   ├── vector_store.py # ChromaDB 封装
│   │   ├── retriever.py   # 混合检索（向量+BM25）
│   │   ├── generator.py   # LLM 生成（带引用）
│   │   ├── rag_engine.py  # RAG 引擎（串联所有模块）
│   │   └── session.py     # 多轮对话管理
│   ├── storage/           # SQLite 持久化
│   └── config.py          # 配置管理
├── data/                  # 知识库文件
├── frontend/              # Vue 3 前端
├── tests/                 # 测试用例
├── main.py                # FastAPI 启动入口
├── build_index.py         # 构建向量索引
└── evaluate.py            # 评测脚本
```

## 配置说明

关键配置在 `src/config.py`，可通过环境变量覆盖：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| CHUNK_SIZE | 800 | 切片大小 |
| CHUNK_OVERLAP | 100 | 切片重叠 |
| RETRIEVAL_TOP_K | 10 | 检索返回数量 |
| USE_HYBRID_RETRIEVAL | true | 启用混合检索 |
| RELEVANCE_THRESHOLD | 0.01 | 相关性阈值 |
| LLM_TEMPERATURE | 0.7 | LLM 温度 |
| MAX_HISTORY_ROUNDS | 5 | 多轮对话保留轮数 |

## License

MIT
