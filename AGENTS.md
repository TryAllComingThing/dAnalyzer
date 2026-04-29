# dAnalyzer — Agent 系统说明

> 多 Agent 路由 + 数据分析执行体系
> 版本: 5.0

---

## 系统架构

```
SessionStart（hooks/session-routing.md 注入）
    │
    ▼
用户输入 → 语义意图分类路由
    │
    ├── DATA_ANALYSIS → Agent 工具 spawn 子 Agent: danalyzer
    ├── RESEARCH      → Agent 工具 spawn 子 Agent: research（预留）
    ├── COMMAND       → 主会话直接执行
    └── GENERAL       → 主会话正常处理
              │
              └── 路由准确性自检 + Red Flag 检查
                    │
                    ├── 异常 → spawn Agent: error-handler
                    └── 子 agent 路由不匹配 → 输出 [reroute: target] 请求重路由
```

**Reroute 协议：** Agent 发现路由不匹配时输出 `[reroute: target]` 请求重路由。主会话捕获后重新路由。

### Spawn 执行流

DATA_ANALYSIS / RESEARCH 命中时，主会话使用 **Agent 工具** spawn 子 agent：

```
主会话路由命中 → Agent({ subagent_type: "general-purpose", prompt: "..." })
    ↓
子 agent 加载指令（agents/danalyzer.md + AGENTS.md）
    ↓
子 agent 自主执行：需求拆解 → 技能编排 → 加载 SKILL → 执行 → security
    ↓
子 agent 返回结果给主会话呈现
```

---

## Agent 列表

| Agent | 文件 | 路由优先级 | 触发信号 | 职责 |
|-------|------|-----------|---------|------|
| **danalyzer** | `agents/danalyzer.md` | DATA_ANALYSIS | 语义判断：数据查询/统计/分析/对比/建模/看板/报表/图表 | 数据分析专家，执行查询→清洗→建模→可视化→报告全链路 |
| **research** | *已预留* | RESEARCH | 语义判断：行业研究/竞品分析/白皮书/PPT/综合报告 | 深度研究报告撰写 |
| **error-handler** | `agents/error-handler.md` | — 异常处理 | 执行中异常触发 | 错误分类/重试/降级/中止决策 |

---

## 路由规则

| 路由目标 | 意图分类 | 说明 |
|---------|---------|------|
| Agent: danalyzer | DATA_ANALYSIS | 涉及数据查询/分析/建模/可视化/报表 |
| Agent: research | RESEARCH | 涉及研究报告/调研/白皮书/PPT |
| 主会话直接执行 | COMMAND | 以 `/` 开头的斜杠命令 |
| 主会话正常处理 | GENERAL | 编程/Git/运维/日常对话等非数据类请求 |

---

## 执行流程

Agent 被路由命中后，按以下流程执行数据分析：

```
需求解析 → 确定分析类型（描述性/诊断性/预测性/规范性/探索性）
    │
    ├── 简单任务（≤2 技能）→ 直接执行
    └── 复杂任务（>2 技能或有依赖）→ 给出执行计划后再执行
    │
    ▼
技能编排 → 按需加载 SKILL.md → 执行
    │
    ├── 1. data-query（查询）
    ├── 2. data-clean（清洗，按需）
    ├── 3. data-clean（可选质量校验）
    ├── 4. data-analysis / model（分析/建模）
    ├── 5. visual / report / dashboard（输出）
    └── 6. security（安全脱敏，强制）
    │
    ▼
交付 → 数据 + 图表 + 文字洞察
```

---

## Skill 技能组合示例

| 用户需求 | 技能组合 |
|----------|----------|
| 销售周报 | data-query → data-clean → data-analysis → visual → report → security |
| 用户RFM | data-query → model(rfm) → visual → security |
| 简单查询 | data-query → security |
| 漏斗分析 | data-query → model(funnel) → visual → security |
| 复杂分析 | data-query → data-clean → data-analysis → model → visual → security |

---

## 安全规范

所有数据输出必须经过 security 处理：

```
输出流程: ... → 输出技能 → security → 最终输出
                              ↑
                      脱敏 + 合规检查（强制）
```

**禁止行为**:
- ❌ 导出未脱敏的 PII 数据
- ❌ 绕过 security 直接输出
- ❌ 记录敏感信息到日志

---

## 核心原则

1. **Skill 规则优先** — SKILL.md 中定义的标准优先于通用知识
2. **不预设固定流程** — 根据需求自主编排技能组合
3. **可跳过不需要的步骤** — 如不需要清洗则跳过
4. **安全优先** — 输出前必须 security 处理
5. **数据 I/O 使用 Connector** — 禁止手写数据读写

---

## 相关文件

- [hooks/session-routing.md](hooks/session-routing.md) — 路由规则（SessionStart 注入）
- [agents/README.md](agents/README.md) — Agent 体系文档
- [CLAUDE.md](CLAUDE.md) — 核心规范
