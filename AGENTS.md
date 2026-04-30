# dAnalyzer — Agent 系统参考

> 版本: 5.0
> 用途: **架构参考文档（仅供人工查阅，不注入运行时上下文）**

**运行时路由决策以 `hooks/routing-table.md`（SessionStart 注入）为准。Agent 执行边界以 `agents/danalyzer.md` 为准。技能编排以 `skills/danalyzer-core/SKILL.md` 为准。**

---

## Agent 目录

| Agent | 文件 | 职责 |
|-------|------|------|
| danalyzer | `agents/danalyzer.md` | 数据分析全链路（查询→清洗→建模→可视化→报告） |
| research | *已预留* | 深度研究报告撰写 |
| error-handler | `agents/error-handler.md` | 错误类型分析/重试/降级/中止决策 |

---

## 系统架构

```
SessionStart（hooks/routing-table.md 注入）
    │
    ▼
用户输入 → 语义意图分类路由（5 级：COMMAND/DATA_DEEP/RESEARCH/DATA_SIMPLE/GENERAL）
    │
    ├── DATA_DEEP  → spawn Agent: danalyzer
    ├── RESEARCH   → spawn Agent: research（预留）
    ├── COMMAND    → 主会话直接执行
    └── GENERAL    → 主会话正常处理
              │
              └── AI 自检 + Red Flag 检查 → 异常 → spawn error-handler
```

### Spawn 执行流

```
主会话路由命中 → Agent({ subagent_type: "general-purpose", prompt: "..." })
    ↓
子 agent 加载 agents/danalyzer.md（执行边界 + 红线）
    ↓
子 agent 自主执行：需求拆解 → 技能编排 → 加载 SKILL → 执行 → security
    ↓
子 agent 返回结果给主会话呈现
```

---

## Reroute 协议

Agent 发现路由不匹配时输出 `[reroute: target]` 请求重路由，主会话捕获后重新路由。

---

## 核心原则

1. **Skill 规则优先** — SKILL.md 中定义的标准优先于通用知识
2. **不预设固定流程** — 根据需求自主编排技能组合
3. **可跳过不需要的步骤** — 如不需要清洗则跳过
4. **安全优先** — 输出前必须 security 处理
5. **数据 I/O 使用 Connector** — 禁止手写数据读写

---

*架构参考用途，不参与运行时路由与决策。*
