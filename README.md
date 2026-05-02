# dAnalyzer Plugin

> 数分ECC - 数据分析企业命令中心 | 配置化数据分析自动化平台

## 简介

dAnalyzer 是一个基于 Claude Code 的数据分析 Plugin，提供完整的数据分析能力，包括数据查询、清洗、分析、报告生成、合规检查等。

**设计理念**：按需加载 + 自主决策

---

## 目录结构

```
dAnalyzer/
├── agents/              # 智能体 (3个)
├── skills/              # 技能 (12个)
├── hooks/               # Hook 脚本 + 多 Agent 路由规则
├── connectors/          # 工具对接 (9个)
├── knowledge/           # 领域知识资产
├── commands/            # 快捷指令 (7个)
├── learn/               # 学习系统
├── output/              # 输出目录
├── tests/               # 测试
├── scripts/             # 脚本
└── CLAUDE.md            # 核心规范
```

---

## 核心组件

### 1. 多 Agent 路由系统

通过 `hooks/session-routing.md` 在 SessionStart 注入 3 级优先级路由：

| 优先级 | 路由目标 | 触发信号 |
|--------|---------|---------|
| 1 | **Commands**（直接执行） | `/quick` `/query` 等命令 |
| 2 | **Agent: danalyzer** | 分析/趋势/对比/归因/漏斗/留存/RFM/聚类/预测/图表/看板/SQL/清洗/建模 |
| 3 | **Agent: research** | `/research` `/report`、研究报告/调研/白皮书/PPT/总结/建议（预留） |

**优先级裁决：** 多规则同时命中时编号小的优先。非数据分析请求直接回答。

### 2. 智能体 (Agents)

| Agent | 路由优先级 | 职责 |
|-------|-----------|------|
| **danalyzer** | 2 — 数据分析 | 数据分析专家：查询→清洗→建模→可视化→报告全链路 |
| **research** | 3 — 研究报告 (预留) | 深度研究报告/调研/PPT/总结建议 |
| **error-handler** | — 异常处理 | 错误分类/重试/降级/中止决策 |

### 3. 技能 (Skills) — 12个

| 技能 | 说明 | 子技能数 |
|------|------|----------|
| data-query | 多数据源查询（含高级查询） | 1 |
| data-clean | 数据清洗 | 6 |
| data-analysis | 统计分析 | - |
| model | 数据建模（RFM/漏斗/归因/聚类/预测/留存） | 8+ |
| report | 报告生成 | 6 |
| security | 安全脱敏 + 合规检查 | 7+ |
| visual | 可视化 | 7 |
| dashboard | 仪表盘 | 7 |
| insight-gen | 洞察生成 | - |
| context-retriever | 行业数据检索 | - |

### 4. 快捷指令 (Commands) — 7个

| 指令 | 说明 |
|------|------|
| /help | 多层帮助入口 |
| /query nl | 自然语言查询 |
| /query sql | SQL 查询 |
| /analysis trend | 趋势分析 |
| /analysis rfm | RFM 分析（→ model 技能） |
| /analysis funnel | 漏斗分析（→ model 技能） |
| /report weekly | 周报生成 |

---

## 设计理念

| 理念 | 说明 |
|------|------|
| **按需加载** | Skills 元数据预加载，完整指令仅在需要时 Read |
| **自主决策** | Agent 根据用户需求自主决定使用哪些技能，不预设固定流程 |
| **灵活组合** | 根据实际需求动态组合技能，可跳过不需要的步骤 |

---

## 版本

- v4.2 (2026-04-29) - 简化架构，删除重复/未使用的技能和 agent 文件，修复文档
- v4.1 (2026-04-29) - 多 Agent 路由体系，3 级优先级路由，Red Flag 拦截
- v4.0 (2026-04-28) - 技能合并精简（18→12），执行纪律规则务实化
- v3.0 (2026-04-25) - 初始版本

---

## 相关文档

- [DSIGN.md](DSIGN.md) — 核心规范
- [AGENTS.md](AGENTS.md) — Agent 系统说明
- [agents/README.md](agents/README.md) — Agent 体系文档
- [skills/README.md](skills/README.md) — 技能说明
- [connectors/README.md](connectors/README.md) — 连接器说明
- [hooks/session-routing.md](hooks/session-routing.md) — 路由规则

---

MIT
