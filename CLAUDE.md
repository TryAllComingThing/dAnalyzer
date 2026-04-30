# dAnalyzer 架构参考

> 版本: 4.2 (2026-04-29)
> 说明: Claude Code 数据分析 Agent 系统
> 设计理念: 按需加载 + 自主决策 + 行业适配 + Skill 规则优先
> 用途: **架构参考文档（仅供人工查阅，不注入运行时上下文）**

**运行时路由决策以 `hooks/routing-table.md`（SessionStart 注入）为准。运行时执行决策以 `skills/danalyzer-core/SKILL.md` 为准。**

---

## 1. 核心设计理念

| 理念 | 说明 |
|------|------|
| **按需加载** | Skills 元数据预加载，完整指令仅在需要时 Read |
| **自主决策** | 根据用户需求动态选择技能组合，不预设固定流程 |
| **Skill 规则优先** | SKILL.md 中定义的评分标准、计算公式优先于通用知识 |
| **灵活组合** | 可跳过不需要的步骤，按实际需求编排 |

---

## 2. 技能与 Agent 目录（12 技能 + 3 Agent）

### 技能

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

### Agent

| Agent | 职责 | 文件 |
|-------|------|------|
| danalyzer | 数据分析全链路（查询/清洗/建模/可视化/报告） | agents/danalyzer.md |
| research | 深度研究报告/调研/PPT/总结建议（预留） | *待创建* |
| error-handler | 错误类型分析/重试/降级/中止决策 | agents/error-handler.md |

---

## 3. 规则体系（4 级）

| 级别 | 优先级 | 用途 |
|------|--------|------|
| legal/ | 最高 | 法律级合规规则（拦截式校验） |
| core/ | 高 | 企业级核心规则（强制生效） |
| base/ | 中 | 基础规范规则（建议性） |
| dynamic/ | 低 | 动态规则（临时合规、口径变更） |

---

## 4. 数据资产

| 目录 | 用途 |
|------|------|
| `data/industry/` | 行业配置（可切换：电商/物流/制造/金融） |
| `data/industry/_base/` | 通用基础配置（indicators/scenarios/mappings） |
| `data/model/` | 通用分析模型 |
| `data/template/` | SQL/报告/导出模板 |

---

## 5. 目录结构

```
dAnalyzer/
├── skills/          # 技能（12 个）
├── agents/          # Agent 定义（含 README.md 体系文档）
├── rules/           # 规则（4 级）
├── connectors/      # 数据源连接器（统一 I/O 接口）
├── data/            # 数据资产（行业配置/模型/模板）
├── learn/           # 学习系统（instincts/patterns）
├── commands/        # 快捷指令
└── hooks/           # 自动化脚本 + 路由表（routing-table.md）
```

---

*本文档于 2026-04-29 更新 (v4.2)。架构参考用途，不参与运行时路由与决策。*
