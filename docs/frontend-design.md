# RAG智能问答系统 — 前端技术方案

> 前端框架：Vue 3 + Vite + TypeScript
> UI组件库：Element Plus（中文生态好、组件全）
> 实时通信：WebSocket（打字机效果）
> 状态管理：Pinia（轻量）
> HTTP请求：axios

---

## 页面设计

### 主页面（单页应用，不需要路由）

```
┌──────────────────────────────────────────────────────┐
│  🧠 RAG 智能问答助手                    [知识库统计]  │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │ 📚 知识库状态：23个文档 | 586个知识片段          │ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │ 💬 对话区域（可滚动）                            │ │
│  │                                                  │ │
│  │  ┌──────────────────────────────────────────┐   │ │
│  │  │ 👤 你：什么是RAG？                       │   │ │
│  │  └──────────────────────────────────────────┘   │ │
│  │                                                  │ │
│  │  ┌──────────────────────────────────────────┐   │ │
│  │  │ 🤖 AI：                                  │   │ │
│  │  │ RAG是检索增强生成技术[1]，核心流程分三步  │   │ │
│  │  │ [2]...                                   │   │ │
│  │  │                                          │   │ │
│  │  │ 📚 参考来源                              │   │ │
│  │  │ ┌──────────────────────────────────┐     │   │ │
│  │  │ │ ▶ [1] 03-RAG检索增强生成.md      │     │   │ │
│  │  │ │   相关度：92%                     │     │   │ │
│  │  │ │   RAG的全称是Retrieval-Augmented  │     │   │ │
│  │  │ │   Generation，中文叫检索增强生成  │     │   │ │
│  │  │ └──────────────────────────────────┘     │   │ │
│  │  │ ┌──────────────────────────────────┐     │   │ │
│  │  │ │ ▶ [2] 04-LangChain基础.md        │     │   │ │
│  │  │ │   相关度：85%                     │     │   │ │
│  │  │ └──────────────────────────────────┘     │   │ │
│  │  │                                          │   │ │
│  │  │ ⏱ 检索 45ms | 生成 1.2s | Token 700    │   │ │
│  │  │ [👍 有用] [👎 没用]                      │   │ │
│  │  └──────────────────────────────────────────┘   │ │
│  │                                                  │ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │ [输入你的问题...                          ] [发送]│ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │ 📄 文档管理（可折叠）                            │ │
│  │ [上传文档] [查看文档列表]                        │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 组件拆分

```
src/
├── App.vue                    # 主页面
├── main.ts                    # 入口
├── components/
│   ├── ChatMessage.vue        # 单条消息（用户/AI）
│   ├── SourceCard.vue         # 引用来源卡片（可展开/折叠）
│   ├── ChatInput.vue          # 输入框 + 发送按钮
│   ├── MessageFeedback.vue    # 反馈按钮（赞/踩）
│   ├── StatsBar.vue           # 知识库统计信息
│   ├── DocumentManager.vue    # 文档管理（上传/列表/删除）
│   └── StreamingText.vue      # 打字机效果组件
├── composables/
│   ├── useWebSocket.ts        # WebSocket连接管理
│   ├── useChat.ts             # 对话逻辑（发送/接收/历史）
│   └── useDocument.ts         # 文档管理逻辑
├── stores/
│   └── chat.ts                # Pinia状态（对话历史、设置）
├── types/
│   └── index.ts               # TypeScript类型定义
└── styles/
    └── main.css               # 全局样式
```

---

## WebSocket消息协议

### 客户端→服务端

```json
// 发送问题
{"action": "query", "question": "什么是RAG？", "session_id": "xxx"}

// 上传文档（如果需要通过WebSocket）
{"action": "upload", "filename": "xxx.md", "content": "base64..."}
```

### 服务端→客户端

```json
// 流式回答（打字机效果，逐token推送）
{"type": "token", "content": "RAG是"}

// 检索结果（回答前先推送）
{"type": "sources", "sources": [
    {"file": "03-RAG.md", "section": "什么是RAG", "score": 0.92, "content": "..."},
    {"file": "04-LangChain.md", "section": "检索链路", "score": 0.85, "content": "..."}
]}

// 回答完成
{"type": "done", "usage": {"prompt_tokens": 520, "completion_tokens": 180}, "timing": {"retrieval_ms": 45, "generation_ms": 1200}}

// 错误
{"type": "error", "message": "检索失败：知识库为空"}

// 文档列表
{"type": "documents", "documents": [
    {"id": "doc_001", "filename": "03-RAG.md", "chunks": 42, "indexed_at": "2026-06-08"}
]}
```

---

## 关键交互实现

### 1. 打字机效果

WebSocket收到token类型消息时，逐字追加到当前消息：
```
收到 {"type":"token","content":"RAG"} → 显示 "RAG"
收到 {"type":"token","content":"是"}  → 显示 "RAG是"
收到 {"type":"token","content":"检索"} → 显示 "RAG是检索"
收到 {"type":"done"} → 显示引用来源卡片
```

### 2. 引用展开/折叠

引用[1][2][3]渲染为可点击的标签。
点击后展开对应的SourceCard，显示原文片段、来源文件、相关度。
再次点击折叠。

### 3. 对话历史

Pinia store维护messages数组：
```typescript
interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    sources?: Source[]
    timing?: Timing
    feedback?: 'positive' | 'negative' | null
}
```

### 4. 文档上传

- 点击"上传文档"→ 文件选择框（限制.md/.txt/.docx/.pdf）
- 上传到 POST /api/v1/documents/upload
- 上传成功后刷新文档列表

---

## 后端接口对接

前端通过两种方式和后端通信：

**WebSocket（主要）：**
- 连接地址：ws://localhost:8080/ws
- 用于：发送问题、接收流式回答、反馈

**HTTP REST（辅助）：**
- 文档管理：GET/POST/DELETE /api/v1/documents
- 健康检查：GET /api/v1/health
- 统计信息：GET /api/v1/stats
- API Key管理：POST /api/v1/keys

---

## 构建和部署

```bash
# 开发
cd frontend
npm install
npm run dev          # 本地开发服务器 http://localhost:5173

# 生产构建
npm run build        # 输出到 dist/
```

**部署方式：**
- 方案A：FastAPI直接serve静态文件（简单，前后端同源）
- 方案B：Nginx反向代理前端+后端（正式部署用）

推荐方案A：FastAPI serve Vue构建产物，不需要额外配置CORS。
后端server.py添加：
```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

---

## 暗色主题

默认暗色主题（科技感），CSS变量控制：
```css
:root {
    --bg-primary: #0F172A;      /* 深蓝背景 */
    --bg-secondary: #1E293B;    /* 卡片背景 */
    --text-primary: #E2E8F0;    /* 主文字 */
    --text-secondary: #94A3B8;  /* 次要文字 */
    --accent: #3B82F6;          /* 强调色（蓝色） */
    --success: #10B981;         /* 成功（绿色） */
    --error: #EF4444;           /* 错误（红色） */
}
```
