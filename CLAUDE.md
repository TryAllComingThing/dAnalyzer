# dAnalyzer 核心规范

> 版本: 4.0 (2026-04-28)
> 说明: Claude Code 数据分析 Agent 系统
> 设计理念: 按需加载 + 自主决策 + 行业适配 + Skill 规则优先

---

## 0. 路由指令（SessionStart 注入 · 最高优先级）

**当用户请求涉及以下任何信号时，MUST 调用 `Skill: danalyzer-core`（主会话内运行）：**

- 数据查询/分析/建模/报表/可视化意图
- 关键词：分析、趋势、对比、归因、漏斗、留存、RFM、聚类、预测、日报、周报、看板、画图、图表、SQL、导出
- 数据源提及：数据库、ClickHouse、Hive、MySQL

**排除：** 纯代码问题、Git 操作、文件管理、系统运维

**不确定时**: 宁可多路由，不可漏路由 → 走 danalyzer-core

---

## 1. 核心设计理念

| 理念 | 说明 |
|------|------|
| **按需加载** | Skills 元数据预加载，完整指令仅在需要时 Read |
| **自主决策** | 根据用户需求动态选择技能组合，不预设固定流程 |
| **Skill 规则优先** | SKILL.md 中定义的评分标准、计算公式优先于通用知识 |
| **灵活组合** | 可跳过不需要的步骤，按实际需求编排 |

---

## 2. 技能列表（13个）

| 技能 | 用途 |
|------|------|
| **danalyzer-core** | 核心调度器（唯一入口） |
| danalyzer-guide | 入门引导 |
| data-query | 多数据源查询（含高级查询：聚合/跨库/时间区间） |
| data-clean | 数据清洗（空值/异常/重复/格式/文本） |
| data-quality-check | 质量校验 |
| data-analysis | 统计分析（描述性/趋势/相关性/分布） |
| model | 数据建模（RFM/漏斗/归因/聚类/预测/留存/相关性） |
| visual | 可视化（ECharts 图表/HTML 自适应多端） |
| report | 报告生成（日报/周报/月报/临时/对比） |
| security | 安全脱敏 + 合规检查（敏感检测/脱敏/审计） |
| context-retriever | 行业数据检索 |
| dashboard | 仪表盘（布局/组件/实时/告警/导出） |
| insight-gen | 洞察生成 |

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
用户输入 → 命中检测？→ Skill: danalyzer-core（主会话内运行）
              │
              ├── 需求理解 → 需求拆解（if 模糊）→ 任务规划（if 复杂）
              ├── 技能决策 → Read SKILL.md → 按 Skill 规则执行
              ├── security（输出前强制脱敏）
              └── 异常 → spawn error-handler（唯一 spawn）
```

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
├── skills/          # 技能（13个）
├── agents/          # 智能体（error-handler + 路由规则）
├── rules/           # 规则（4级）
├── connectors/      # 数据源连接器（Python: MySQL/ClickHouse/Hive/CSV/Excel）
├── data/            # 数据资产（行业配置/模型/模板）
├── learn/           # 学习系统（instincts/patterns）
├── commands/        # 快捷指令
└── hooks/           # 自动化脚本
```

---

*本文档于 2026-04-28 更新 (v4.0)*
