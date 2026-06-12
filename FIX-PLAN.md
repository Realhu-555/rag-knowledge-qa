# 修复计划 — 2026-06-12

当前状态：385 个测试，372 passed / **13 failed** / 1 skipped
Ruff lint：**70 errors**（54 unused-import, 6 f-string, 5 unused-variable, 2 import-order, 2 ambiguous-name, 1 redefined）

---

## 一、修复 13 个失败测试

### 1.1 test_generator.py（3 个失败）

**根因：** generator.py 重构了 prompt 模板和 import 方式，测试未同步。

| 测试 | 失败原因 | 修复方式 |
|------|---------|---------|
| `test_build_prompt` | 断言 `"[1]" in prompt`，但 prompt 改为 `(文件名，章节名)` 格式 | 更新断言：检查 `rag.md` 和 `简介` 在 prompt 中 |
| `test_build_prompt_includes_rules` | 断言 `"不要编造" in prompt`，但 prompt 模板已改写 | 更新断言：检查当前 prompt 中的实际规则文本 |
| `test_generate_calls_llm` | mock `src.core.generator.OpenAI`，但 OpenAI 是在 `_init_client` 内部 import 的 | 改为 mock `openai.OpenAI`，或 patch `_init_client` 方法 |

### 1.2 test_splitter.py + test_loaders.py（2 个失败）

**根因：** MarkdownSplitter 新增了短 section 合并逻辑（< 100 字符的 section 向后合并），测试用的文本太短。

| 测试 | 失败原因 | 修复方式 |
|------|---------|---------|
| `test_split_by_headers` | 每个 section 内容约 10 字，全部被合并为 1 个 chunk | 增加每个 section 的内容长度（> 100 字符），或改为断言合并后的行为 |
| `test_text_markdown_style_split` | 同上 | 同上 |

**推荐：** 增加内容长度，让每个 section 超过 100 字符，验证按标题切分仍然生效。

### 1.3 test_m5.py（3 个失败）

**根因：** `RELEVANCE_THRESHOLD` 默认值从 0.3 改为 0.01，测试断言未更新。

| 测试 | 失败原因 | 修复方式 |
|------|---------|---------|
| `test_threshold_config_default` | `assert RELEVANCE_THRESHOLD == 0.3`，实际 0.01 | 改为 `== 0.01` |
| `test_threshold_filters_low_score` | 阈值 0.3 时代入过滤逻辑，但实际阈值是 0.01 | 改用 `RELEVANCE_THRESHOLD` 变量而非硬编码 0.3 |
| `test_cached_results_below_threshold_not_used_as_sources` | 期望 0.05/0.1 被过滤，但阈值 0.01 不会过滤它们 | 同上，使用实际 config 值 |

**注意：** rag_engine.py 第 282 行 `final_results = [r for r in final_results if r.score > -10]` 已经移除了阈值过滤，缓存路径也用 `RELEVANCE_THRESHOLD`。测试需要和实际行为对齐。

### 1.4 test_m8.py（4 个失败）

| 测试 | 失败原因 | 修复方式 |
|------|---------|---------|
| `test_summary_injected_into_system` | mock `src.core.generator.OpenAI` 不存在 | 改为 mock `openai.OpenAI`（或 patch `_init_client`） |
| `test_no_summary_normal_system` | 同上 | 同上 |
| `test_history_injected_between_system_and_user` | 同上 | 同上 |
| `test_followup_triggered_on_low_score_with_history` | 用 `__new__` 创建 RAGEngine 跳过 `__init__`，缺少 `self.generator` | 添加 `engine.generator = Mock()` |

---

## 二、清理 Ruff lint 错误（70 个）

### 2.1 自动修复（60 个 fixable）

```bash
ruff check src/ tests/ --fix
```

可自动修复：
- F401 unused-import（54 个）— 删除未使用的 import
- F541 f-string-missing-placeholders（6 个）— 改为普通字符串
- F811 redefined-while-unused（1 个）

### 2.2 手动修复（10 个）

| 类型 | 数量 | 处理方式 |
|------|------|---------|
| F841 unused-variable | 5 | 删除未使用的变量或加 `_` 前缀 |
| E402 module-import-not-at-top | 2 | 移到文件顶部（如果不会引起循环导入） |
| E741 ambiguous-variable-name | 2 | 重命名变量（如 `l` → `line`） |

---

## 三、SPEC 与实现对齐

以下 SPEC 描述和实际代码不一致，需要更新 SPEC.md：

| 项目 | SPEC 写的 | 实际实现 | 修复 |
|------|----------|---------|------|
| chunk_size | 500 | 800 | 更新 SPEC 为 800 |
| chunk_overlap | 50 | 100 | 更新 SPEC 为 100 |
| 引用格式 | `[1][2][3]` 编号 | `(文件名，章节名)` | 更新 SPEC 中的 prompt 模板示例 |
| 前端 | Gradio | Vue 3 + Element Plus | 更新 SPEC Phase 4 描述 |
| 评测集 | 10 个问题 | 30 条测试用例 | 更新 SPEC 为 30 |

---

## 四、添加 Pre-commit Hook

新增 `.pre-commit-config.yaml`，防止未来退化：

```yaml
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check
        entry: ruff check --fix
        language: system
        types: [python]
        pass_filenames: true

      - id: ruff-format
        name: ruff format
        entry: ruff format
        language: system
        types: [python]
        pass_filenames: true
```

安装：
```bash
pip install pre-commit
pre-commit install
```

---

## 五、执行顺序

1. `ruff check src/ tests/ --fix` — 自动修复 60 个 lint 错误
2. 手动修复剩余 10 个 lint 错误
3. 修复 13 个失败测试（按 1.1 → 1.4 顺序）
4. 更新 SPEC.md 对齐实际实现
5. 添加 `.pre-commit-config.yaml`
6. 全量验证：`pytest tests/ -v` + `ruff check src/ tests/` — 确认 0 失败 0 error
