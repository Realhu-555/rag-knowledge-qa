# RAG智能问答系统

企业级RAG智能问答助手，支持多格式文档、查询理解、回答可追溯、开放API。

## 技术栈

Python / LangChain / ChromaDB / DeepSeek / Gradio / FastAPI

## 快速开始

```bash
# 1. 安装依赖
uv venv .venv
uv pip install -r requirements.txt

# 2. 配置API Key
cp .env.example .env
# 编辑 .env 填入 DeepSeek API Key

# 3. 构建索引
python build_index.py

# 4. 启动Gradio界面
python app.py

# 5. 或启动API服务
python main.py
```

## 项目结构

详见 SPEC: 知识库/.hermes/plans/2026-06-08_170200-rag-knowledge-qa-SPEC.md
