# dAnalyzer Plugin

> 数分ECC - 数据分析企业命令中心 | 配置化数据分析自动化平台

## 简介

dAnalyzer 是一个基于 Claude Code 的数据分析 Plugin，提供完整的数据分析能力，包括数据查询、清洗、分析、报告生成、合规检查等。

**设计理念**：按需加载 + 自主决策 (参考 Everything Claude Code)

---

## 目录结构

```
dAnalyzer/
├── agents/              # 智能体 (2个)
├── skills/              # 技能 (13个, 57个文件)
├── rules/               # 规则 (19个, 4级)
├── checks/              # 校验钩子 (15个)
├── connectors/          # 工具对接 (9个)
├── data/                # 数据资产 (28个)
├── commands/            # 快捷指令 (7个)
├── docs/                # 文档
├── learn/               # 学习系统
├── scripts/             # 脚本
└── CLAUDE.md            # 核心规范
```

---

## 核心组件

### 1. 智能体 (Agents)

| Agent | 说明 |
|-------|------|
| use-danalyzer | 路由规则（SessionStart 注入） |
| error-handler | 错误处理（唯一 spawn Agent） |

**核心执行入口**：`Skill: danalyzer-core` - 主会话内运行，根据用户需求自主决定调用哪些技能

### 2. 技能 (Skills) - 13个

| 技能 | 说明 | 子技能数 |
|------|------|----------|
| data-query | 多数据源查询（含高级查询） | 1 |
| data-clean | 数据清洗 | 6 |
| data-analysis | 统计分析 | - |
| data-quality-check | 数据质量检查 | - |
| model | 数据建模（RFM/漏斗/归因/聚类/预测/留存） | 8+ |
| report | 报告生成 | 6 |
| security | 安全脱敏 + 合规检查 | 7+ |
| visual | 可视化 | 7 |
| dashboard | 仪表盘 | 7 |
| insight-gen | 洞察生成 | - |
| danalyzer-guide | 入门指南 | - |
| context-retriever | 行业数据检索 | - |

### 3. 规则 (Rules) - 19个

| 级别 | 数量 | 说明 |
|------|------|------|
| legal | 4 | 法律级 - 最高优先级，违规终止 |
| core | 5 | 企业核心 - 强制生效 |
| base | 5 | 基础规范 - 建议遵循 |
| dynamic | 4 | 动态规则 - 临时生效 |

### 4. 快捷指令 (Commands) - 7个

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
| **Skill 规则优先** | SKILL.md 中定义的评分标准、计算公式优先于通用知识 |
| **灵活组合** | 根据实际需求动态组合技能，可跳过不需要的步骤 |

---

## 版本

- v4.0 (2026-04-28) - 技能合并精简（18→12），执行纪律规则务实化
- v3.1 (2026-04-25) - 精简 agents，删除重复文件和预设流程
- v3.0 (2026-04-25) - 初始版本

---

## 相关文档

- [CLAUDE.md](CLAUDE.md) - 核心规范
- [AGENTS.md](AGENTS.md) - Agent 说明
- [skills/README.md](skills/README.md) - 技能说明
- [rules/README.md](rules/README.md) - 规则说明
- [connectors/README.md](connectors/README.md) - 连接器说明

---

MIT
