# dAnalyzer 核心规范

> 版本: 4.2 (2026-04-29)
> 说明: Claude Code 数据分析 Agent 系统
> 设计理念: 按需加载 + 自主决策 + 行业适配 + Skill 规则优先

---

## 强制路由协议（最高优先级）

**在响应用户之前，必须执行以下路由流程，禁止跳过：**

```
┌──────────────────────────────────────────────┐
│ 步骤 1: 分析用户输入 → 匹配路由触发信号        │
│ 步骤 2: 按优先级表选择路由目标                  │
│ 步骤 3: spawn 或直接执行                      │
│ 步骤 4: 输出 [路由] 标记到对话                 │
└──────────────────────────────────────────────┘
```

### 执行规则
1. 优先级 1-3 必须 spawn Agent，非数据分析请求直接回答
2. 子 Agent 输出 `[reroute: target]` 时，主 Agent 必须重新 spawn
3. 路由后自检：输出 `[路由] 目标: X | 触发词: Y`

### 路由表

| 优先级 | 路由目标 | 触发信号 | 启动方式 |
|--------|---------|---------|---------|
| 1 | **data-query** | `/quick` `/query`、仅查询/导出 | `Agent({subagent_type: "skill", ...})` |
| 2 | **Agent: danalyzer** | 分析/趋势/对比/漏斗/RFM/图表/看板/SQL/建模等 | `Agent({subagent_type: "danalyzer", ...})` |
| 3 | **Agent: research** (预留) | 研究报告/调研/PPT/总结建议 | `Agent({subagent_type: "research", ...})` |

---

## 1. 核心设计理念

| 理念 | 说明 |
|------|------|
| **按需加载** | Skills 元数据预加载，完整指令仅在需要时 Read |
| **自主决策** | 根据用户需求动态选择技能组合，不预设固定流程 |
| **Skill 规则优先** | SKILL.md 中定义的评分标准、计算公式优先于通用知识 |
| **灵活组合** | 可跳过不需要的步骤，按实际需求编排 |

---

## 2. 技能与 Agent 列表（12技能 + 3 Agent）

| 技能 | 用途 |
|------|------|
| danalyzer-guide | 入门引导 |
| data-query | 多数据源查询（含高级查询：聚合/跨库/时间区间） |
| data-clean | 数据清洗 + 质量校验（空值/异常/重复/格式/文本） |
| data-analysis | 统计分析（描述性/趋势/相关性/分布） |
| model | 数据建模（RFM/漏斗/归因/聚类/预测/留存/相关性） |
| visual | 可视化（ECharts 图表/HTML 自适应多端） |
| report | 报告生成（日报/周报/月报/临时/对比） |
| security | 安全脱敏 + 合规检查（敏感检测/脱敏/审计） |
| context-retriever | 行业数据检索 |
| dashboard | 仪表盘（布局/组件/实时/告警/导出） |
| insight-gen | 洞察生成 |

**Agent 路由目标（由 hooks/session-routing.md 按优先级路由）：**

| Agent/Skill | 路由优先级 | 职责 | 文件 |
|------------|-----------|------|------|
| **data-query** | 1 — 简单取数 | 直接数据查询/导出 | skills/data-query/SKILL.md |
| **danalyzer** | 2 — 数据分析 | 数据分析专家：查询/清洗/建模/可视化/报告 | agents/danalyzer.md |
| **research** | 3 — 研究报告 (预留) | 深度研究报告/调研/PPT/总结建议 | *待创建* |
| **error-handler** | — 异常处理 | 错误类型分析/重试/降级/中止决策 | agents/error-handler.md |

---

## 3. 规则体系（4级）

| 级别 | 优先级 | 用途 |
|------|--------|------|
| legal/ | 最高 | 法律级合规规则（拦截式校验） |
| core/ | 高 | 企业级核心规则（强制生效） |
| base/ | 中 | 基础规范规则（建议性） |
| dynamic/ | 低 | 动态规则（临时合规、口径变更） |

---

## 4. 执行模型

```
SessionStart（Hook 注入路由规则 hooks/session-routing.md）
    │
    ▼
用户输入 → 多 Agent 路由判定（按优先级 1→3）
    │
    ├── 优先级 1 → 路由到 Skill: data-query（简单取数）
    ├── 优先级 2 → 路由到 Agent: danalyzer（数据分析）
    ├── 优先级 3 → 路由到 Agent: research（研究报告，预留）
    └── 非数据分析 → 直接回答
              │
              └── 路由准确性自检 + Red Flag 检查
                    │
                    └── 异常 → spawn error-handler

**技能组合示例**:

| 用户需求 | 技能组合 |
|----------|----------|
| 销售周报 | data-query → data-clean → data-analysis → visual → report → security |
| 用户RFM | data-query → model(rfm) → visual → security |
| 简单查询 | data-query → security |
| 漏斗分析 | data-query → model(funnel) → visual → security |

---

## 5. 数据资产

| 目录 | 用途 |
|------|------|
| `data/industry/` | 行业配置（可切换：电商/物流/制造/金融） |
| `data/industry/_base/` | 通用基础配置（indicators/scenarios/mappings） |
| `data/model/` | 通用分析模型 |
| `data/template/` | SQL/报告/导出模板 |

---

## 6. 目录结构

```
dAnalyzer/
├── skills/          # 技能（12个）
├── agents/          # 智能体（含 README.md 完整体系文档）
├── rules/           # 规则（4级）
├── connectors/      # 数据源连接器（Python: MySQL/ClickHouse/Hive/CSV/Excel）
├── data/            # 数据资产（行业配置/模型/模板）
├── learn/           # 学习系统（instincts/patterns）
├── commands/        # 快捷指令
└── hooks/           # 自动化脚本 + 多 Agent 路由（session-routing.md）+ 计分配置（routing_config.yaml）
```

---

*本文档于 2026-04-29 更新 (v4.2)*
