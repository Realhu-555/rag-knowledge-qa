# AI应用工程师完整知识手册

> 从零到一，覆盖AI应用工程师所需的全部技术栈。看不懂随时问。

---

# 第一部分：基础工程能力

---

## 1. Python 核心基础

### 1.1 为什么选 Python

Python 是 AI 领域的"普通话"。几乎所有大模型框架（LangChain、LlamaIndex、HuggingFace）都以 Python 为第一优先级。原因：
- 生态丰富：AI/ML 库几乎都先出 Python 版本
- 上手简单：语法接近伪代码，非科班也能快速产出
- 动态类型：开发速度快，适合快速原型验证

### 1.2 虚拟环境管理

**问题**：不同项目可能需要不同版本的库，混在一起会冲突。

**Conda**（推荐新手）：
```bash
# 安装 Miniconda（轻量版 Anaconda）
# 创建虚拟环境
conda create -n myproject python=3.11

# 激活环境
conda activate myproject

# 安装包
pip install fastapi uvicorn

# 导出环境
conda env export > environment.yml

# 从文件恢复
conda env create -f environment.yml
```

**Poetry**（推荐进阶）：
```bash
# 安装 Poetry
pip install poetry

# 创建新项目
poetry new myproject
cd myproject

# 添加依赖
poetry add fastapi uvicorn
poetry add --group dev pytest

# 运行
poetry run python main.py

# 生成 lock 文件（锁定版本）
poetry lock
```

**区别**：
- Conda：管理 Python 版本 + 系统级依赖（如 C 库），适合数据科学
- Poetry：纯 Python 依赖管理，更适合工程开发

### 1.3 FastAPI 框架

FastAPI 是当前最流行的 Python Web 框架之一，专为 API 开发设计。

**安装**：
```bash
pip install fastapi uvicorn
```

**最简单的 API**：
```python
# main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, AI World!"}

# 运行：uvicorn main:app --reload
# 访问：http://localhost:8000
# 自动文档：http://localhost:8000/docs
```

**带参数的 API**：
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# 定义数据模型（请求体）
class ChatRequest(BaseModel):
    message: str
    model: str = "gpt-4"  # 默认值

class ChatResponse(BaseModel):
    reply: str
    tokens_used: int

# POST 接收 JSON 请求体
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # 这里调用大模型
    reply = f"你说了：{request.message}"
    return ChatResponse(reply=reply, tokens_used=10)

# GET 带路径参数
@app.get("/user/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": "张三"}

# GET 带查询参数
@app.get("/search")
async def search(q: str, page: int = 1):
    return {"query": q, "page": page}
```

**运行**：
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**关键概念**：
- `@app.get()` / `@app.post()`：装饰器定义路由
- `BaseModel`：Pydantic 数据模型，自动校验请求参数
- `async def`：异步函数，后面会详细讲
- `--reload`：代码改动后自动重启，开发时必用

### 1.4 异步编程 async/await

**为什么需要异步**：

假设你要调用大模型 API，一次请求要等 2 秒。同步模式下：
```
请求1 → 等2秒 → 请求2 → 等2秒 → 请求3 → 等2秒
总耗时：6秒
```

异步模式下：
```
请求1 → 请求2 → 请求3 → (同时等) → 全部完成
总耗时：约2秒
```

**代码对比**：
```python
import asyncio
import time

# 同步版本
def sync_fetch(url):
    time.sleep(2)  # 模拟网络请求
    return f"Data from {url}"

# 异步版本
async def async_fetch(url):
    await asyncio.sleep(2)  # 异步等待，不阻塞
    return f"Data from {url}"

# 同步：串行执行
start = time.time()
for url in ["url1", "url2", "url3"]:
    sync_fetch(url)
print(f"同步耗时：{time.time() - start:.1f}s")  # 约6秒

# 异步：并发执行
async def main():
    start = time.time()
    tasks = [async_fetch(url) for url in ["url1", "url2", "url3"]]
    results = await asyncio.gather(*tasks)  # 同时执行所有任务
    print(f"异步耗时：{time.time() - start:.1f}s")  # 约2秒

asyncio.run(main())
```

**实际场景 — 并发调用大模型**：
```python
import httpx
import asyncio

async def call_llm(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            json={"model": "gpt-4", "messages": [{"role": "user", "content": prompt}]},
            headers={"Authorization": "Bearer your-key"},
            timeout=30.0
        )
        return response.json()["choices"][0]["message"]["content"]

async def main():
    prompts = ["什么是RAG？", "什么是Agent？", "什么是Prompt Engineering？"]
    tasks = [call_llm(p) for p in prompts]
    results = await asyncio.gather(*tasks)
    for p, r in zip(prompts, results):
        print(f"Q: {p}\nA: {r}\n")

asyncio.run(main())
```

**一句话总结**：`async/await` 让你在等待 I/O（网络、文件、数据库）时去做别的事，而不是傻等。

---

## 2. 数据库

### 2.1 MySQL — 关系型数据库

**核心概念**：
- **表（Table）**：数据存在表里，像 Excel 的 sheet
- **行（Row）**：一条记录
- **列（Column）**：一个字段
- **主键（Primary Key）**：唯一标识一行的字段
- **索引（Index）**：加速查询的数据结构

**基本操作（SQL）**：
```sql
-- 创建表
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(200) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入数据
INSERT INTO users (name, email) VALUES ('张三', 'zhangsan@example.com');

-- 查询
SELECT * FROM users WHERE name = '张三';
SELECT * FROM users ORDER BY created_at DESC LIMIT 10;

-- 更新
UPDATE users SET email = 'new@example.com' WHERE id = 1;

-- 删除
DELETE FROM users WHERE id = 1;
```

**Python 操作 MySQL**：
```python
# pip install pymysql
import pymysql

# 连接数据库
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='your_password',
    database='myapp',
    charset='utf8mb4'
)

try:
    with conn.cursor() as cursor:
        # 查询
        cursor.execute("SELECT * FROM users WHERE name = %s", ("张三",))
        result = cursor.fetchall()
        
        # 插入
        cursor.execute(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            ("李四", "lisi@example.com")
        )
        conn.commit()  # 提交事务
finally:
    conn.close()
```

**索引优化**：
```sql
-- 没有索引：全表扫描（慢）
SELECT * FROM users WHERE email = 'test@example.com';

-- 加索引：B+树查找（快）
CREATE INDEX idx_email ON users(email);
SELECT * FROM users WHERE email = 'test@example.com';  -- 快很多

-- 复合索引
CREATE INDEX idx_name_email ON users(name, email);
```

**什么时候加索引**：
- WHERE 条件经常用到的字段
- JOIN 关联的字段
- ORDER BY 排序的字段
- 不要加太多索引：会减慢写入速度

### 2.2 Redis — 缓存与消息队列

Redis 是内存数据库，读写速度比 MySQL 快 100 倍以上。

**核心数据结构**：
```bash
# 字符串（最简单）
SET user:1:name "张三"
GET user:1:name  # → "张三"
SETEX token:abc123 3600 "user_data"  # 设置带过期时间的值

# 哈希（类似字典）
HSET user:1 name "张三" age 25 email "zhangsan@example.com"
HGET user:1 name  # → "张三"
HGETALL user:1  # → {"name": "张三", "age": "25", ...}

# 列表（队列/栈）
LPUSH queue:tasks "task1"  # 左边插入
RPUSH queue:tasks "task2"  # 右边插入
LPOP queue:tasks  # 左边取出

# 集合（不重复）
SADD tags:post:1 "python" "ai" "fastapi"
SMEMBERS tags:post:1  # → {"python", "ai", "fastapi"}

# 有序集合（排行榜）
ZADD leaderboard 100 "player1"
ZADD leaderboard 200 "player2"
ZREVRANGE leaderboard 0 9  # 前10名
```

**Python 操作 Redis**：
```python
# pip install redis
import redis

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# 缓存大模型结果（避免重复调用）
def get_llm_response(prompt: str) -> str:
    cache_key = f"llm:{hash(prompt)}"
    
    # 先查缓存
    cached = r.get(cache_key)
    if cached:
        return cached  # 命中缓存，直接返回
    
    # 缓存未命中，调用大模型
    response = call_llm_api(prompt)
    
    # 存入缓存，1小时过期
    r.setex(cache_key, 3600, response)
    return response

# 简单的消息队列
def push_task(task_data: str):
    r.lpush("task_queue", task_data)

def pop_task() -> str:
    return r.rpop("task_queue")
```

**Redis 在 AI 应用中的典型用途**：
- **会话缓存**：存储用户对话历史，避免每次都查数据库
- **限流**：API 调用频率限制
- **任务队列**：异步处理耗时的 AI 任务
- **分布式锁**：多个 worker 防止重复处理

### 2.3 向量数据库 — RAG 的核心

**什么是向量**：

把一段文本转换成一串数字（向量），语义相近的文本，向量也相近。

```
"我喜欢猫"  → [0.2, 0.8, 0.1, 0.5, ...]  （1536维）
"我养了一只猫" → [0.22, 0.78, 0.12, 0.48, ...]  （很接近）
"今天天气好"  → [0.9, 0.1, 0.7, 0.3, ...]  （差距很大）
```

**向量数据库的作用**：
传统数据库用 SQL 查精确匹配，向量数据库用"相似度"查语义匹配。

**Milvus 快速上手**：
```python
# pip install pymilvus
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

# 连接
connections.connect("default", host="localhost", port="19530")

# 定义 schema
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2000),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536)
]
schema = CollectionSchema(fields, description="Document embeddings")
collection = Collection("documents", schema)

# 插入数据（embedding 需要先用模型生成）
import openai
def get_embedding(text):
    client = openai.OpenAI(api_key="your-key")
    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    return response.data[0].embedding

docs = ["Python是一门编程语言", "FastAPI是Python的Web框架", "Redis是缓存数据库"]
embeddings = [get_embedding(doc) for doc in docs]

collection.insert([docs, embeddings])

# 搜索相似文档
query = "什么框架用来写API？"
query_embedding = get_embedding(query)

results = collection.search(
    data=[query_embedding],
    anns_field="embedding",
    param={"metric_type": "L2", "params": {"nprobe": 10}},
    limit=3,
    output_fields=["text"]
)

for hit in results[0]:
    print(f"相似度: {hit.score:.4f}, 文本: {hit.entity.get('text')}")
```

**Qdrant 快速上手**（更轻量，推荐新手）：
```python
# pip install qdrant-client
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

# 启动（内存模式，无需安装服务）
client = QdrantClient(":memory:")

# 创建集合
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
)

# 插入
client.upsert(
    collection_name="documents",
    points=[
        PointStruct(id=1, vector=get_embedding("Python"), payload={"text": "Python是一门编程语言"}),
        PointStruct(id=2, vector=get_embedding("FastAPI"), payload={"text": "FastAPI是Web框架"}),
    ]
)

# 搜索
results = client.search(
    collection_name="documents",
    query_vector=get_embedding("写API用什么"),
    limit=3
)
```

**向量数据库选型**：
| 数据库 | 特点 | 适用场景 |
|--------|------|----------|
| Milvus | 功能全、性能强 | 大规模生产环境 |
| Qdrant | 轻量、好上手 | 中小项目、快速原型 |
| ChromaDB | 最简单、纯 Python | 学习和小项目 |
| Pinecone | 全托管、无需运维 | 不想自己部署 |

---

## 3. Docker 容器化

### 3.1 核心概念

**Docker 解决什么问题**："在我机器上能跑啊！"

把你的代码 + 依赖 + 运行环境打包成一个"容器"，在任何地方都能一致运行。

**类比**：
- **镜像（Image）**：一个只读的模板，比如 Ubuntu + Python + 你的代码
- **容器（Container）**：镜像跑起来的实例，就像类和对象的关系
- **Dockerfile**：构建镜像的说明书
- **Docker Compose**：管理多个容器的编排工具

### 3.2 Dockerfile 编写

```dockerfile
# 基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件（利用缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**requirements.txt**：
```
fastapi==0.115.0
uvicorn==0.30.0
httpx==0.27.0
```

**构建和运行**：
```bash
# 构建镜像
docker build -t my-ai-app .

# 运行容器
docker run -d -p 8000:8000 --name my-app my-ai-app

# 查看日志
docker logs my-app

# 进入容器调试
docker exec -it my-app bash

# 停止并删除
docker stop my-app && docker rm my-app
```

### 3.3 Docker Compose — 编排多个服务

一个 AI 应用通常有多个组件：Web 服务 + Redis + 数据库 + 向量数据库。

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
      - MILVUS_HOST=milvus
    depends_on:
      - redis
      - db
      - milvus
    volumes:
      - .:/app  # 开发时挂载代码，改代码自动生效

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: myapp
    volumes:
      - pgdata:/var/lib/postgresql/data

  milvus:
    image: milvusdb/milvus:v2.4-latest
    ports:
      - "19530:19530"

volumes:
  pgdata:
```

**启动所有服务**：
```bash
docker compose up -d       # 启动
docker compose down         # 停止并删除
docker compose logs -f web  # 查看 web 服务日志
docker compose ps           # 查看所有服务状态
```

### 3.4 常用 Docker 命令速查

```bash
# 镜像操作
docker images                    # 列出所有镜像
docker rmi image_name            # 删除镜像
docker system prune -a           # 清理无用镜像和容器

# 容器操作
docker ps                        # 查看运行中的容器
docker ps -a                     # 查看所有容器（包括停止的）
docker stop container_name       # 停止容器
docker rm container_name         # 删除容器
docker logs container_name       # 查看日志
docker exec -it container_name bash  # 进入容器

# 网络
docker network ls                # 查看网络
docker network create mynet      # 创建自定义网络
```

---

## 4. Linux 基础

### 4.1 常用命令

```bash
# 文件操作
ls -la                    # 列出文件（含隐藏文件）
cd /path/to/dir           # 切换目录
pwd                       # 显示当前路径
mkdir -p a/b/c            # 递归创建目录
cp source dest            # 复制
mv source dest            # 移动/重命名
rm -rf dir                # 强制递归删除（慎用！）

# 文件查看
cat file.txt              # 查看文件全部内容
head -n 20 file.txt       # 查看前20行
tail -f log.txt           # 实时查看日志（调试神器）
less file.txt             # 分页查看（q退出）
grep "error" log.txt      # 搜索关键词
grep -r "TODO" ./src      # 递归搜索目录

# 权限
chmod 755 script.sh       # 设置权限（rwxr-xr-x）
chmod +x script.sh        # 添加执行权限
chown user:group file     # 修改所有者

# 进程管理
ps aux | grep python      # 查找进程
top                       # 实时查看系统资源
htop                      # 更好看的 top（需要安装）
kill PID                  # 终止进程
kill -9 PID               # 强制终止

# 网络
curl http://localhost:8000  # HTTP 请求
netstat -tlnp              # 查看端口占用
ss -tlnp                   # 更现代的端口查看
wget http://example.com/file  # 下载文件

# 磁盘
df -h                      # 查看磁盘使用
du -sh /path               # 查看目录大小
free -h                    # 查看内存使用
```

### 4.2 服务管理（systemd）

```bash
# 查看服务状态
sudo systemctl status nginx

# 启动/停止/重启
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx

# 设置开机自启
sudo systemctl enable nginx
sudo systemctl disable nginx

# 查看日志
journalctl -u nginx -f        # 实时查看
journalctl -u nginx --since "1 hour ago"  # 最近1小时
```

---

# 第二部分：AI应用核心开发能力

---

## 5. 大模型基础认知

### 5.1 Transformer 是什么

Transformer 是当前所有大语言模型（GPT、Claude、Llama 等）的底层架构。

**核心思想 — 自注意力机制（Self-Attention）**：

人类读句子时，会自动关联上下文。比如：
> "小明把苹果放到了桌子上，然后**它**就离开了"

"它"指代什么？人类靠上下文理解。Transformer 也是这样工作的。

```
"它" → 关注 "苹果"（权重 0.7）
"它" → 关注 "小明"（权重 0.2）
"它" → 关注 "桌子"（权重 0.1）
```

模型通过计算每个词与其他词的"注意力分数"来理解语义关系。

**Token 是什么**：

大模型不直接处理文字，而是把文字切成 Token（词元）。

```
"我喜欢吃苹果" → ["我", "喜欢", "吃", "苹果"]  （4个token）
"I love apples" → ["I", " love", " apple", "s"]  （4个token）
```

**上下文窗口（Context Window）**：

模型一次能处理的最大 Token 数。比如 GPT-4 的上下文窗口是 128K Token，约 10 万字中文。

超过这个限制，模型就"记不住"前面的内容了。

### 5.2 Prompt Engineering

Prompt 是你和大模型沟通的语言。好的 Prompt = 好的结果。

**基础原则**：
```python
# ❌ 差的 Prompt
"写一篇文章"

# ✅ 好的 Prompt
你是一位资深技术博主，请用通俗易懂的语言，写一篇关于RAG技术的博客文章。
要求：
1. 标题吸引人
2. 用生活化的比喻解释技术概念
3. 包含代码示例
4. 字数800-1000字
```

**Few-Shot 学习（给例子）**：
```python
prompt = """
请判断用户评论的情感是正面还是负面。

评论：这个产品太好用了！
情感：正面

评论：质量很差，不推荐。
情感：负面

评论：还行吧，没什么特别的。
情感：中性

评论：发货很快，包装也很好。
情感：
"""
# 模型会学习你给的例子，输出"正面"
```

**思维链（Chain of Thought）**：
```python
# ❌ 直接问
prompt = "123 * 456 = ?"

# ✅ 让模型展示推理过程
prompt = """
请一步一步计算 123 * 456：

第一步：...
第二步：...
最终答案：
"""
```

**结构化 Prompt 模板**：
```python
SYSTEM_PROMPT = """你是一个{role}。
你的任务是{task}。

规则：
1. {rule1}
2. {rule2}
3. {rule3}

输出格式：
{format_example}
"""

def build_prompt(role, task, rule1, rule2, rule3, format_example):
    return SYSTEM_PROMPT.format(
        role=role, task=task,
        rule1=rule1, rule2=rule2, rule3=rule3,
        format_example=format_example
    )
```

---

## 6. RAG — 检索增强生成

### 6.1 什么是 RAG

**问题**：大模型的知识截止到训练日期，且可能产生幻觉（编造事实）。

**解决方案**：先检索相关文档，再让模型基于这些文档生成答案。

```
用户问题 → 检索相关文档 → 把文档+问题一起给模型 → 生成答案
```

**类比**：开卷考试 vs 闭卷考试。RAG 让模型"开卷答题"。

### 6.2 RAG 完整流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  文档加载     │ →  │  文本分割     │ →  │  向量化      │
│  (Loader)    │    │  (Splitter)  │    │  (Embedding) │
└─────────────┘    └─────────────┘    └─────────────┘
                                              ↓
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  生成答案     │ ←  │  检索+排序    │ ←  │  存入向量库   │
│  (Generator) │    │  (Retriever) │    │  (VectorDB)  │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 6.3 逐步实现

**Step 1: 文档加载**
```python
# pip install langchain langchain-community

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    UnstructuredMarkdownLoader
)

# 加载 PDF
loader = PyPDFLoader("document.pdf")
docs = loader.load()  # 返回 Document 对象列表

# 加载 Markdown
loader = UnstructuredMarkdownLoader("readme.md")
docs = loader.load()

# 加载纯文本
loader = TextLoader("data.txt", encoding="utf-8")
docs = loader.load()
```

**Step 2: 文本分割**
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 为什么要分割？
# 大模型有上下文窗口限制，且检索太长的文档效果差
# 需要切成合适大小的"块"（chunk）

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,      # 每块最大500字符
    chunk_overlap=50,    # 块之间重叠50字符（保持上下文连贯）
    separators=["\n\n", "\n", "。", "！", "？", ".", " "]
)

chunks = text_splitter.split_documents(docs)
print(f"原始文档数: {len(docs)}, 分割后块数: {len(chunks)}")
```

**Step 3: 向量化并存入向量库**
```python
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# 初始化 embedding 模型
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 存入 Chroma（最简单的向量库）
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db"  # 持久化到磁盘
)
```

**Step 4: 检索**
```python
# 相似度检索
retriever = vectorstore.as_retriever(
    search_type="similarity",  # 相似度搜索
    search_kwargs={"k": 3}     # 返回最相似的3个文档
)

# 检索
query = "什么是RAG？"
relevant_docs = retriever.invoke(query)

for doc in relevant_docs:
    print(f"来源: {doc.metadata.get('source', 'unknown')}")
    print(f"内容: {doc.page_content[:200]}")
    print("---")
```

**Step 5: 生成答案**
```python
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

# Prompt 模板
template = """
基于以下参考资料回答问题。如果资料中没有相关信息，请说"根据已有资料无法回答"。

参考资料：
{context}

问题：{question}

回答：
"""

prompt = ChatPromptTemplate.from_template(template)

# LLM
llm = ChatOpenAI(model="gpt-4", temperature=0)

# 构建 RAG 链
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# 使用
answer = rag_chain.invoke("什么是RAG技术？")
print(answer)
```

### 6.4 RAG 优化技巧

**1. 分块策略优化**
```python
# 按语义分割（更智能）
from langchain_experimental.text_splitter import SemanticChunker

semantic_splitter = SemanticChunker(
    embeddings,
    breakpoint_threshold_type="percentile",
    breakpoint_percentile_threshold=85
)
chunks = semantic_splitter.split_documents(docs)
```

**2. 混合检索（Hybrid Search）**
```python
# 结合关键词搜索 + 向量搜索
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

# BM25 关键词检索
bm25_retriever = BM25Retriever.from_documents(chunks)
bm25_retriever.k = 3

# 向量检索
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 混合检索（各占50%权重）
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.5, 0.5]
)
```

**3. 重排序（Re-ranking）**
```python
# 初步检索后，用更精确的模型重新排序
from langchain.retrievers import ContextualCompressionRetriever
from langchain_cohere import CohereRerank

# Cohere 重排序
reranker = CohereRerank(model="rerank-v3.5", top_n=3)
compression_retriever = ContextualCompressionRetriever(
    base_compressor=reranker,
    base_retriever=vector_retriever
)
```

---

## 7. Agent 开发

### 7.1 什么是 Agent

**传统程序**：人写好每一步，程序按顺序执行。
**Agent**：给模型一个目标和工具，它自己规划怎么完成。

```
用户：帮我查一下北京今天的天气，然后推荐穿什么

Agent 的思考过程：
1. 需要查天气 → 调用天气 API
2. 得到结果：北京今天 28°C，晴
3. 基于天气推荐穿搭
4. 返回答案
```

**Agent = LLM + 工具 + 记忆 + 规划**

### 7.2 LangGraph — 构建复杂 Agent

LangGraph 是 LangChain 团队出品的 Agent 框架，用"图"来组织 Agent 的工作流。

**安装**：
```bash
pip install langgraph langchain-openai
```

**最简单的 Agent**：
```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

# 定义工具
@tool
def search_web(query: str) -> str:
    """搜索互联网获取最新信息"""
    # 这里接入搜索 API
    return f"搜索结果：关于 '{query}' 的最新信息..."

@tool
def calculate(expression: str) -> str:
    """计算数学表达式"""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误：{e}"

# 创建 Agent
llm = ChatOpenAI(model="gpt-4", temperature=0)
agent = create_react_agent(llm, [search_web, calculate])

# 运行
result = agent.invoke({
    "messages": [("user", "今天比特币多少钱？帮我算一下买3个要多少钱")]
})

print(result["messages"][-1].content)
```

### 7.3 自定义 Agent 工作流

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage

# 定义状态
class AgentState(TypedDict):
    messages: list
    next_step: str

# 定义节点（每个节点是一个处理步骤）
def research_node(state: AgentState) -> AgentState:
    """研究节点：搜索信息"""
    last_msg = state["messages"][-1].content
    # 调用搜索工具...
    search_result = f"关于'{last_msg}'的研究结果"
    state["messages"].append(AIMessage(content=search_result))
    return state

def analyze_node(state: AgentState) -> AgentState:
    """分析节点：分析搜索结果"""
    # 分析逻辑...
    state["next_step"] = "respond"
    return state

def respond_node(state: AgentState) -> AgentState:
    """回复节点：生成最终答案"""
    # 生成回复...
    state["messages"].append(AIMessage(content="最终答案"))
    return state

# 定义路由逻辑
def should_continue(state: AgentState) -> str:
    if state.get("next_step") == "respond":
        return "respond"
    return "analyze"

# 构建图
workflow = StateGraph(AgentState)
workflow.add_node("research", research_node)
workflow.add_node("analyze", analyze_node)
workflow.add_node("respond", respond_node)

workflow.set_entry_point("research")
workflow.add_conditional_edges("research", should_continue)
workflow.add_edge("analyze", "respond")
workflow.add_edge("respond", END)

app = workflow.compile()

# 运行
result = app.invoke({
    "messages": [HumanMessage(content="分析AI行业趋势")],
    "next_step": ""
})
```

### 7.4 Agent 核心概念

**工具调用（Tool Calling）**：
```python
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气信息
    
    Args:
        city: 城市名称，如"北京"、"上海"
    """
    # 实际项目中调用天气 API
    return f"{city}今天晴，28°C"

# 模型会自动决定什么时候调用哪个工具
# 关键：tool 的 docstring 要写清楚，模型靠这个决定何时使用
```

**记忆管理**：
```python
from langgraph.checkpoint.memory import MemorySaver

# 短期记忆（对话历史）
memory = MemorySaver()
agent = create_react_agent(llm, [get_weather], checkpointer=memory)

# 多轮对话
config = {"configurable": {"thread_id": "user-123"}}

result1 = agent.invoke(
    {"messages": [("user", "北京天气怎么样？")]},
    config
)

result2 = agent.invoke(
    {"messages": [("user", "那明天呢？")]},  # Agent 记得上一轮在问北京
    config
)
```

---

## 8. 微调入门 — LoRA

### 8.1 什么时候需要微调

- Prompt Engineering 和 RAG 搞不定时
- 需要模型学习特定风格/格式
- 需要模型掌握专有领域知识

### 8.2 LoRA 原理

**全量微调**：修改模型所有参数 → 需要巨大显存，成本高
**LoRA**：只训练一小部分"旁路"参数 → 省显存，效果接近

```
原始模型权重 W (冻结，不动)
    ↓
输入 x → [W] → 输出
    ↓
输入 x → [A×B] → 额外输出（A和B是可训练的低秩矩阵）
    ↓
最终输出 = W(x) + A×B(x)
```

**显存需求对比**：
- 全量微调 7B 模型：需要 ~28GB 显存
- LoRA 微调 7B 模型：需要 ~4GB 显存

### 8.3 实操示例

```python
# pip install peft transformers datasets accelerate

from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer
from datasets import Dataset

# 加载基座模型
model_name = "Qwen/Qwen2-7B"
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# 准备训练数据
train_data = Dataset.from_dict({
    "text": [
        "用户：什么是RAG？\n助手：RAG（检索增强生成）是一种结合检索和生成的技术...",
        "用户：解释LoRA\n助手：LoRA是一种参数高效微调方法...",
    ]
})

# LoRA 配置
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=8,                    # 低秩矩阵的秩（越大效果越好，显存需求越高）
    lora_alpha=32,          # 缩放因子
    lora_dropout=0.1,       # dropout 防过拟合
    target_modules=["q_proj", "v_proj"]  # 对哪些层做 LoRA
)

# 应用 LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()  # → trainable params: 4,194,304 / 7,000,000,000 (0.06%)

# 训练配置
training_args = TrainingArguments(
    output_dir="./lora_output",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    learning_rate=2e-4,
    logging_steps=10,
    save_strategy="epoch",
)

# 训练
trainer = SFTTrainer(
    model=model,
    train_dataset=train_data,
    args=training_args,
    tokenizer=tokenizer,
    max_seq_length=2048,
)

trainer.train()

# 保存 LoRA 权重（只有几MB）
model.save_pretrained("./my_lora_adapter")

# 推理时加载
from peft import PeftModel
base_model = AutoModelForCausalLM.from_pretrained(model_name)
model = PeftModel.from_pretrained(base_model, "./my_lora_adapter")
```

---

# 第三部分：工程落地与系统迭代

---

## 9. LangSmith — 全链路追踪

### 9.1 为什么需要观测

AI 系统是"黑盒"——你不知道模型为什么给出某个答案。LangSmith 帮你看到每次调用的：
- 输入了什么 Prompt
- 模型输出了什么
- 调用了哪些工具
- 每一步花了多少时间
- 消耗了多少 Token

### 9.2 接入

```python
# pip install langsmith

import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-langsmith-key"
os.environ["LANGCHAIN_PROJECT"] = "my-rag-app"

# 之后所有 LangChain/LangGraph 调用都会自动追踪
# 在 LangSmith 网站查看：https://smith.langchain.com
```

### 9.3 自定义追踪

```python
from langsmith import traceable

@traceable(name="my-rag-pipeline")
def rag_pipeline(question: str) -> str:
    # 这个函数的输入输出会被记录
    docs = retrieve_documents(question)
    answer = generate_answer(question, docs)
    return answer

# 查看追踪
# 在 LangSmith 网站可以看到每次调用的详细信息
```

---

## 10. 性能优化

### 10.1 异步并发

```python
import asyncio
import httpx

async def call_model_batch(prompts: list[str]) -> list[str]:
    """并发调用大模型"""
    async with httpx.AsyncClient() as client:
        tasks = []
        for prompt in prompts:
            task = client.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": prompt}]
                },
                headers={"Authorization": "Bearer your-key"},
                timeout=30.0
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        return [r.json()["choices"][0]["message"]["content"] for r in responses]
```

### 10.2 降级策略

```python
async def call_model_with_fallback(prompt: str) -> str:
    """模型调用 + 降级"""
    try:
        # 优先用 GPT-4
        return await call_gpt4(prompt)
    except (TimeoutError, RateLimitError):
        try:
            # GPT-4 不可用，降级到 GPT-3.5
            return await call_gpt35(prompt)
        except Exception:
            # 都不可用，返回兜底回答
            return "抱歉，AI 服务暂时不可用，请稍后再试。"
```

### 10.3 缓存策略

```python
import hashlib
import json
import redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def cached_llm_call(prompt: str, ttl: int = 3600) -> str:
    """带缓存的 LLM 调用"""
    cache_key = f"llm:{hashlib.md5(prompt.encode()).hexdigest()}"
    
    # 查缓存
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # 调用模型
    result = call_llm(prompt)
    
    # 写缓存
    redis_client.setex(cache_key, ttl, json.dumps(result))
    return result
```

---

## 11. 完整项目实战：AI面试助手

把前面学的所有技术串起来。

### 11.1 项目结构

```
ai-interview-helper/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── rag.py               # RAG 核心逻辑
│   ├── llm.py               # 大模型调用
│   ├── models.py            # Pydantic 数据模型
│   └── vectorstore.py       # 向量库操作
├── data/
│   └── resumes/             # 上传的简历存放
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

### 11.2 核心代码

```python
# app/main.py
from fastapi import FastAPI, UploadFile, File
from app.models import InterviewRequest, InterviewResponse
from app.rag import RAGPipeline

app = FastAPI(title="AI面试助手")
rag = RAGPipeline()

@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """上传简历"""
    content = await file.read()
    # 保存并索引简历
    doc_id = rag.index_document(content, file.filename)
    return {"doc_id": doc_id, "filename": file.filename}

@app.post("/interview", response_model=InterviewResponse)
async def start_interview(request: InterviewRequest):
    """开始模拟面试"""
    # 基于简历和JD生成面试问题
    questions = rag.generate_questions(
        resume_id=request.resume_id,
        job_description=request.job_description,
        num_questions=request.num_questions or 5
    )
    return InterviewResponse(questions=questions)

@app.post("/evaluate")
async def evaluate_answer(answer: str, question: str):
    """评估回答"""
    feedback = rag.evaluate_answer(answer, question)
    return {"feedback": feedback}
```

```python
# app/rag.py
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter

class RAGPipeline:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0.7)
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = Chroma(
            collection_name="resumes",
            embedding_function=self.embeddings,
            persist_directory="./chroma_db"
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=50
        )
    
    def index_document(self, content: bytes, filename: str):
        """索引文档"""
        text = content.decode("utf-8")
        chunks = self.splitter.split_text(text)
        self.vectorstore.add_texts(chunks, metadatas=[{"source": filename}] * len(chunks))
        return filename
    
    def generate_questions(self, resume_id: str, job_description: str, num_questions: int):
        """基于简历和JD生成面试问题"""
        # 检索简历内容
        resume_docs = self.vectorstore.similarity_search(resume_id, k=3)
        resume_text = "\n".join([doc.page_content for doc in resume_docs])
        
        prompt = f"""你是一位资深面试官。
        
候选人简历：
{resume_text}

目标岗位JD：
{job_description}

请生成{num_questions}个面试问题，涵盖技术能力、项目经验和行为面试。"""
        
        response = self.llm.invoke(prompt)
        return response.content
```

---

# 学习建议

1. **不要死记硬背**：每个技术点都动手写一遍，跑通才算学会
2. **遇到报错别慌**：把错误信息贴给 Cursor/ChatGPT，让它帮你分析
3. **做项目 > 看文档**：以"AI面试助手"为目标，做到哪学到哪
4. **面试时讲故事**：不只是说"我会RAG"，要说"我做过一个RAG系统，遇到了XX问题，用XX方法解决的"
