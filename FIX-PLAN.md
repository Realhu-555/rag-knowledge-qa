# RAG 智能问答系统 — 企业级升级方案

> 最后更新：2026-06-12
> 作者：MiMoCode 评估

---

## 当前状态

| 指标 | 数值 |
|------|------|
| 测试 | 385 passed / 0 failed / 1 skipped |
| Ruff lint | 0 errors |
| Pre-commit | ✅ ruff check + ruff format |
| AGENTS.md | ✅ 已配置 |
| SPEC 对齐 | ❌ 5 处脱节 |
| Docker | ❌ 无 |
| 限流持久化 | ❌ 内存，重启丢失 |
| OCR | ⚠️ 代码有，未启用 |

## 已完成的修复

- [x] 修复 13 个失败测试（mock 路径、阈值不一致、短文本合并）
- [x] 清理 70 个 Ruff lint 错误
- [x] 添加 `.pre-commit-config.yaml`
- [x] 添加 `AGENTS.md`

---

## P0 — 必须做

### 1. 启用 OCR 多模态能力

**目标：** 让系统能处理图片数据（照片、截图、扫描件），OCR 提取文字后纳入知识库。

**改动文件：** `.env`

```bash
# 在 .env 中追加
MULTIMODAL_ENABLED=true
IMAGE_LLM_DESCRIPTION=true
CHART_ANALYSIS_ENABLED=true
OCR_LANGUAGES=chi_sim+eng
TESSERACT_CMD=D:\tesseract\tesseract.exe
```

**改动文件：** `src/core/loaders/image_loader.py`

在 `_ocr_with_tesseract` 方法中，自动检测 Tesseract 路径：

```python
def _ocr_with_tesseract(self, file_path: Path) -> str:
    import pytesseract
    from PIL import Image
    from src.config import OCR_LANGUAGES

    # 优先用配置的路径
    tesseract_cmd = os.getenv("TESSERACT_CMD", "")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    img = Image.open(file_path)
    text = pytesseract.image_to_string(img, lang=OCR_LANGUAGES)
    return text
```

**改动文件：** `src/config.py`

新增一行：

```python
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "tesseract")
```

**验证：**
- `data/` 目录放一张包含中文的图片
- 运行 `python build_index.py`，确认图片被 OCR 索引
- 问一个只有图片里才有的信息，确认能回答

---

### 2. Docker 容器化

**目标：** 一键部署，不依赖手动装 Python 环境。

**新增文件：** `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 系统依赖（Tesseract OCR + 中文语言包）
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY src/ src/
COPY main.py build_index.py evaluate.py manage_keys.py ./
COPY data/ data/

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["python", "main.py"]
```

**新增文件：** `docker-compose.yml`

```yaml
version: "3.8"

services:
  app:
    build: .
    ports:
      - "8080:8080"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./chroma_db:/app/chroma_db
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
    ports:
      - "5173:80"
    depends_on:
      - app
```

**验证：**
- `docker compose up` 一键启动
- `curl http://localhost:8080/health` 返回 ok

---

### 3. SPEC.md 与代码对齐

**改动文件：** `SPEC.md`

以下 5 处需要更新：

| 项目 | SPEC 写的 | 改为 | 原因 |
|------|----------|------|------|
| chunk_size | 500 | 800 | config.py 默认 800 |
| chunk_overlap | 50 | 100 | config.py 默认 100 |
| 引用格式 | `[1][2][3]` 编号 | `(文件名，章节名)` | generator.py 已改为这种格式 |
| 前端 | Gradio | Vue 3 + Element Plus | 已实现 Vue 前端 |
| 评测集 | 10 个问题 | 30 条测试用例 | evaluation/test_cases.json 有 30 条 |

---

### 4. API 限流持久化

**问题：** 当前 `rate_limit.py` 用内存 dict 存限流计数，服务重启后清零。

**改动文件：** `src/api/rate_limit.py`

改为 SQLite 持久化：

```python
"""限流中间件 — SQLite 持久化"""
import time
import sqlite3
from typing import Callable
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from src.config import RATE_LIMIT_DAILY, RATE_LIMIT_PER_MINUTE


def _get_conn():
    conn = sqlite3.connect("rag.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            api_key TEXT,
            minute_ts INTEGER,
            minute_count INTEGER DEFAULT 0,
            daily_date TEXT,
            daily_count INTEGER DEFAULT 0,
            PRIMARY KEY (api_key)
        )
    """)
    conn.commit()
    return conn


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        api_key = auth_header[7:]
        if not api_key:
            return await call_next(request)

        current_time = time.time()
        current_minute = int(current_time // 60)
        current_date = time.strftime("%Y-%m-%d", time.localtime(current_time))

        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT minute_ts, minute_count, daily_date, daily_count FROM rate_limits WHERE api_key=?",
                (api_key,)
            ).fetchone()

            if row is None:
                conn.execute(
                    "INSERT INTO rate_limits VALUES (?, ?, 1, ?, 1)",
                    (api_key, current_minute, current_date)
                )
                conn.commit()
                return await call_next(request)

            minute_ts, minute_count, daily_date, daily_count = row

            # 日期重置
            if daily_date != current_date:
                daily_count = 0
                daily_date = current_date

            # 分钟重置
            if minute_ts != current_minute:
                minute_count = 0
                minute_ts = current_minute

            # 检查限流
            if minute_count >= RATE_LIMIT_PER_MINUTE:
                raise HTTPException(status_code=429, detail="每分钟请求次数超限")
            if daily_count >= RATE_LIMIT_DAILY:
                raise HTTPException(status_code=429, detail="每日请求次数超限")

            # 更新计数
            conn.execute(
                "UPDATE rate_limits SET minute_ts=?, minute_count=?, daily_date=?, daily_count=? WHERE api_key=?",
                (minute_ts, minute_count + 1, daily_date, daily_count + 1, api_key)
            )
            conn.commit()
        finally:
            conn.close()

        return await call_next(request)
```

**验证：**
- 启动服务，连续请求超过 10 次/分钟，确认返回 429
- 重启服务，确认限流计数不丢失

---

## P1 — 应该做

### 5. E2E 测试 mock 化

**问题：** 当前 E2E 测试直接调真实 LLM API，CI 跑不通、不稳定。

**改动文件：** 新增 `tests/conftest.py`（如不存在）

```python
"""测试 fixtures"""
import pytest
from unittest.mock import patch, Mock


@pytest.fixture
def mock_llm():
    """Mock LLM 调用，返回固定响应"""
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="RAG是检索增强生成技术。"))]
    mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    with patch("openai.OpenAI") as mock_cls:
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_cls.return_value = mock_client
        yield mock_client
```

**改动文件：** 新增 `tests/test_e2e_pipeline.py`

```python
"""E2E 测试：完整 RAG 链路（mock LLM）"""
import pytest


@pytest.mark.usefixtures("mock_llm")
class TestRAGPipeline:
    def test_full_query_returns_answer(self):
        """完整链路：提问 → 检索 → 生成 → 带引用"""
        from src.core.rag_engine import RAGEngine
        engine = RAGEngine(use_query_expansion=False, use_hyde=False, use_reranker=False)
        response = engine.query("什么是RAG？", top_k=3)

        assert response.answer
        assert "知识库中未找到" not in response.answer or response.sources == []
        assert isinstance(response.timing, dict)
        assert "total_ms" in response.timing

    def test_empty_query_returns_not_found(self):
        """空查询返回提示"""
        from src.core.rag_engine import RAGEngine
        engine = RAGEngine(use_query_expansion=False, use_hyde=False, use_reranker=False)
        response = engine.query("", top_k=3)

        # 应该优雅处理，不崩溃
        assert response.answer
```

**验证：**
- `pytest tests/test_e2e_pipeline.py -v` 通过，不依赖 API Key

---

### 6. 错误处理标准化

**问题：** 多处 `except Exception: pass` 静默吞错，出问题无法排查。

**改动文件：** 新增 `src/core/errors.py`

```python
"""结构化错误码"""


class RAGError(Exception):
    """RAG 系统基础异常"""
    def __init__(self, code: str, message: str, details: str = ""):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(f"[{code}] {message}")


class RetrievalError(RAGError):
    """检索失败"""
    def __init__(self, details: str = ""):
        super().__init__("RETRIEVAL_FAILED", "检索失败", details)


class GenerationError(RAGError):
    """LLM 生成失败"""
    def __init__(self, details: str = ""):
        super().__init__("GENERATION_FAILED", "LLM 生成失败", details)


class EmbeddingError(RAGError):
    """Embedding 失败"""
    def __init__(self, details: str = ""):
        super().__init__("EMBEDDING_FAILED", "Embedding 失败", details)


class IndexBuildError(RAGError):
    """索引构建失败"""
    def __init__(self, details: str = ""):
        super().__init__("INDEX_BUILD_FAILED", "索引构建失败", details)
```

**改动范围：** 以下文件中的 `except Exception: pass` 需要改为结构化处理：

| 文件 | 行为 | 改为 |
|------|------|------|
| `rag_engine.py:120` | BM25 索引构建失败静默 | `logger.warning` + 记录指标 |
| `query_understander.py:86` | 查询扩展失败静默 | 返回原始 query + `logger.warning` |
| `query_understander.py:121` | HyDE 失败静默 | 返回原始 query + `logger.warning` |
| `generator.py:70` | LLM 调用失败 | 抛出 `GenerationError`，上层捕获返回友好提示 |

**验证：**
- 断开网络，调用 API，确认返回结构化错误而不是空响应

---

## P2 — 锦上添花

### 7. Prometheus 指标暴露

**改动文件：** `src/core/metrics.py`

新增方法：

```python
def to_prometheus(self) -> str:
    """导出 Prometheus 格式指标"""
    lines = []
    for name, value in self._counters.items():
        lines.append(f"# TYPE rag_{name} counter")
        lines.append(f"rag_{name} {value}")
    for name, values in self._histograms.items():
        if values:
            lines.append(f"# TYPE rag_{name} gauge")
            lines.append(f"rag_{name}_avg {sum(values)/len(values):.2f}")
            lines.append(f"rag_{name}_count {len(values)}")
    return "\n".join(lines)
```

**改动文件：** `src/api/routes.py`

新增端点：

```python
@router.get("/metrics/prometheus")
async def prometheus_metrics():
    """Prometheus 格式指标"""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(metrics.to_prometheus(), media_type="text/plain")
```

---

### 8. 向量库健康检查

**改动文件：** `src/core/vector_store.py`

在 `VectorStore` 类新增：

```python
def health_check(self) -> dict:
    """检查向量库连接状态"""
    try:
        count = self.count()
        return {"status": "ok", "collection": self.collection_name, "count": count}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

**改动文件：** `src/api/routes.py`

更新 `/health` 端点：

```python
@router.get("/health", response_model=HealthResponse)
async def health():
    vs_status = vector_store.health_check()
    if vs_status["status"] != "ok":
        return HealthResponse(status="degraded", version="1.1.0")
    return HealthResponse(status="ok", version="1.1.0")
```

---

### 9. SPEC/config 一致性校验脚本

**新增文件：** `scripts/check_consistency.py`

```python
"""检查 SPEC.md 和 config.py 的一致性"""
import re
from pathlib import Path


def check():
    config_text = Path("src/config.py").read_text()
    spec_text = Path("SPEC.md").read_text()

    issues = []

    # 检查 chunk_size
    config_size = re.search(r'CHUNK_SIZE.*?(\d+)', config_text)
    spec_size = re.search(r'chunk_size.*?(\d+)', spec_text)
    if config_size and spec_size and config_size.group(1) != spec_size.group(1):
        issues.append(f"chunk_size: config={config_size.group(1)}, spec={spec_size.group(1)}")

    # 检查 chunk_overlap
    config_overlap = re.search(r'CHUNK_OVERLAP.*?(\d+)', config_text)
    spec_overlap = re.search(r'chunk_overlap.*?(\d+)', spec_text)
    if config_overlap and spec_overlap and config_overlap.group(1) != spec_overlap.group(1):
        issues.append(f"chunk_overlap: config={config_overlap.group(1)}, spec={spec_overlap.group(1)}")

    if issues:
        print("❌ SPEC/config 不一致：")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("✅ SPEC/config 一致")
        return 0


if __name__ == "__main__":
    exit(check())
```

---

## 执行顺序

```
Step 1: 启用 OCR（改 .env + config.py + image_loader.py）
Step 2: SPEC.md 对齐（5 处文本修改）
Step 3: Docker 容器化（新增 Dockerfile + docker-compose.yml）
Step 4: 限流持久化（重写 rate_limit.py）
Step 5: 错误处理标准化（新增 errors.py + 改 4 个文件的 except）
Step 6: E2E 测试 mock 化（新增 conftest.py + test_e2e_pipeline.py）
Step 7: Prometheus 指标（metrics.py 新增方法 + routes.py 新增端点）
Step 8: 向量库健康检查（vector_store.py + routes.py）
Step 9: 一致性校验脚本（新增 scripts/check_consistency.py）
```

每完成一步，运行 `pytest tests/ -v` + `ruff check src/ tests/` 确认无退化。
