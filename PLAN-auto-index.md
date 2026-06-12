# Plan: 自动索引 — 监控 data/ 目录，新文件自动切片+向量化

## Context
当前用户把文件放到 data/ 后需要手动运行 `python build_index.py`。企业级使用需要自动化：文件放入即索引。

## 方案：watchdog 文件监控 + 增量索引

### 核心流程
```
文件放入 data/ → watchdog 检测 → 等待写入完成 → 增量索引 → 自动生效
```

### 需要修改的文件

1. **requirements.txt** — 添加 `watchdog`
2. **新建 `src/core/file_watcher.py`** — 文件监控核心逻辑
3. **main.py** — 服务启动时开启文件监控

### file_watcher.py 设计

```python
class DataDirWatcher:
    """监控 data/ 目录，新文件自动触发增量索引"""

    def __init__(self, data_dir, debounce_seconds=5):
        self.data_dir = data_dir
        self.debounce = debounce_seconds  # 防抖：等文件写入完成
        self._pending = {}  # {path: timestamp}
        self._timer = None

    def start(self):
        """启动监控（非阻塞）"""
        # watchdog Observer 监控 data/ 目录
        # 监听事件：created, modified
        # 新文件 → 加入 _pending → debounce 后触发索引

    def _on_file_event(self, event):
        """文件事件处理"""
        # 过滤：只处理支持的格式（.md, .docx, .pdf 等）
        # 过滤：忽略临时文件（~, .tmp）
        # 加入 _pending，重置 debounce 计时器

    def _trigger_index(self):
        """触发增量索引"""
        # 调用 build_index_incremental() 的核心逻辑
        # 只处理 _pending 中的文件
        # 清空 _pending
```

### 集成到 main.py

```python
# main.py 中启动文件监控
from src.core.file_watcher import DataDirWatcher
watcher = DataDirWatcher(DATA_DIR)
watcher.start()
```

### 关键设计点

1. **防抖机制** — 文件可能还在写入中（大文件复制），等 5 秒无新事件再触发索引
2. **格式过滤** — 只处理 .md, .docx, .pdf, .txt, .png, .jpg
3. **临时文件过滤** — 忽略 ~开头、.tmp 结尾的文件
4. **非阻塞** — 监控在后台线程运行，不影响 API 服务
5. **日志记录** — 每次自动索引记录处理了哪些文件、多少 chunk

### 验证步骤

1. 启动服务：`python main.py`
2. 手动复制一个 .md 文件到 data/ 目录
3. 观察控制台日志：是否自动触发索引
4. 在前端提问新文件相关的问题，确认能检索到
