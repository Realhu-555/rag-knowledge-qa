# RAG 智能问答系统 — 工程改进计划
> 最后更新：2026-06-12

## 当前状态

| 指标 | 数值 |
|------|------|
| 测试 | 385 passed / 0 failed / 1 skipped |
| Ruff lint | 0 errors |
| Pre-commit | ✅ ruff check + ruff format + pytest |
| SPEC 对齐 | ❌ 待处理 |

## 已完成的修复

- [x] 修复 13 个失败测试（mock 路径、阈值不一致、短文本合并）
- [x] 清理 70 个 Ruff lint 错误
- [x] 添加 `.pre-commit-config.yaml`
- [x] 添加 `AGENTS.md`

## 待办：企业级改进

### P0 — 必须做
- [ ] Docker 容器化（Dockerfile + docker-compose）
- [ ] API 限流持久化（Redis 或 SQLite）
- [ ] SPEC.md 与代码对齐（chunk_size、引用格式、前端方案、评测集数量）

### P1 — 应该做
- [ ] E2E 测试 mock 化（mock LLM 调用，CI 离线可跑）
- [ ] 错误处理标准化（结构化错误码 + 日志，替代静默 except pass）

### P2 — 锦上添花
- [ ] Prometheus 指标暴露（/metrics 端点）
- [ ] 向量库健康检查（ChromaDB 连接检测）
- [ ] SPEC/config 一致性校验脚本
