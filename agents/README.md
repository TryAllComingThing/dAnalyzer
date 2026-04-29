# dAnalyzer Agent 体系

> 版本: 1.0 (2026-04-29)
> 路由规则定义在 hooks/session-routing.md，由 SessionStart Hook 注入。

---

## 架构总览

```
SessionStart（hooks/session-routing.md 注入）
    │
    ▼
用户输入 → 多 Agent 路由判定（优先级 1→5）
    │
    ├── 1 → Skill: data-query（简单取数/导出）
    ├── 2 → Agent: use-danalyzer | danalyzer（数据分析）
    ├── 3 → Agent: research（研究报告）[*待创建]
    ├── 4 → Skill: danalyzer-core（复杂跨 Agent 编排）
    └── 5 → 直接回答（不路由）
              │
              └── 路由准确性自检 + Red Flag 检查
                    │
                    └── 异常 → spawn Agent: error-handler
```

---

## 当前 Agent

| Agent | 文件 | 路由优先级 | 触发信号 | 职责 |
|-------|------|-----------|---------|------|
| **danalyzer** | `agents/danalyzer.md` | 2 — 数据分析 | `/data` `/analyze`、分析/趋势/对比/归因/漏斗/留存/RFM/聚类/预测/图表/看板/SQL/建模 | 数据分析专家，执行查询→清洗→建模→可视化→报告全链路 |
| **error-handler** | `agents/error-handler.md` | — 异常处理 | 执行中异常触发 | 错误分类/重试/降级/中止决策 |
| **research** | *待创建* | 3 — 研究报告 | `/research` `/report`、调研/白皮书/PPT/总结/建议 | 深度研究报告撰写 |

---

## Agent 职责边界

### use-danalyzer / danalyzer（数据分析 Agent）

- **输入：** 用户的数据分析需求（含数据源、分析目标、输出形式）
- **能力：** 8 项（数据查询/清洗/质量校验/统计分析/建模/可视化/报告/安全脱敏）
- **分析深度：** 描述性 → 诊断性 → 预测性 → 规范性 → 探索性
- **执行链路：** 2-6 个 Skill 按需组合
- **输出：** 数据 + 图表（ECharts）+ 文字洞察
- **执行纪律：** 必须 Read SKILL.md，Skill 规则优先于通用知识

### danalyzer-core（编排器）

- **输入：** 需要跨 Agent/跨技能协调的复杂请求
- **能力：** 需求理解/拆解/任务规划/技能决策/按需加载/执行编排
- **触发条件：** >2 个技能或任务间有依赖关系
- **输出：** 编排后的综合结果

### error-handler（异常处理）

- **输入：** 错误类型 + 错误消息 + 执行上下文
- **策略：** 重试(临时性) / 跳过(非关键) / 降级(部分不可用) / 中止(致命)
- **输出：** 处理决策 JSON

---

## 路由规则

| 优先级 | 路由目标 | 触发条件 | 排除条件 |
|--------|---------|---------|---------|
| 1 | Skill: data-query | `/quick` `/query`、仅取数/导出/下载 | 含分析/建模/报告意图 |
| 2 | Agent: danalyzer | `/data` `/analyze`、分析/建模/可视化/报表 | — |
| 3 | Agent: research | `/research` `/report`、调研/PPT/总结 | 当前命中时进快速确认 |
| 4 | 直接回答 | 非数据无关请求 | — |

**优先级裁决：** 多规则同时命中时编号小的优先。
**Reroute 协议：** Agent 发现路由不匹配时输出 `[reroute: target]` 请求重路由。

---

## Red Flags（路由前拦截）

详见 `hooks/session-routing.md`：
- 伪分析 / 高风险操作 / 范围过大 / 预测无依据 / 口径模糊
- 触发的暂停路由，使用 AskUserQuestion 澄清

---

## 审计

每次路由后输出：
```
[路由] 输入摘要 → 目标: X | 触发: Y | Reroute: 否 | RedFlag: 无
```

---

*关联文件：hooks/session-routing.md（路由规则）、CLAUDE.md（项目规范）*
