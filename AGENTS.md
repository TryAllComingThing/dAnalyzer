# dAnalyzer — Agent Instructions

> 数据分析核心 Agent 系统
> 版本: 4.0

---

## 设计理念

1. **按需加载** — 仅在需要时 Read SKILL.md
2. **自主决策** — 根据需求动态选择技能组合
3. **Skill 规则优先** — SKILL.md 中定义的标准优先于通用知识
4. **灵活组合** — 可跳过不需要的步骤

---

## 执行入口

danalyzer-core 是**唯一执行入口**，以 Skill 形式在主会话内运行：

```
用户输入 → danalyzer-core（Skill 调用 · 主会话内运行）
    ├── 需求理解 + 需求拆解（if 模糊）+ 任务规划（if 复杂）
    ├── 技能决策 → Read SKILL.md → 按 Skill 规则执行
    └── 异常 → spawn error-handler（唯一 spawn）
```

---

## 可用 Skills（13个）

| 类别 | Skills |
|------|--------|
| 数据查询 | data-query |
| 数据处理 | data-clean, data-quality-check |
| 数据分析 | data-analysis, model |
| 输出 | visual, report, dashboard |
| 安全 | security |
| 辅助 | danalyzer-guide, context-retriever, insight-gen |

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

## 技能组合示例

| 用户需求 | 技能组合 |
|----------|----------|
| 销售周报 | data-query → data-clean → data-analysis → visual → report → security |
| 用户RFM | data-query → model(rfm) → visual → security |
| 简单查询 | data-query → security |
| 漏斗分析 | data-query → model(funnel) → visual → security |

---

## 核心原则

1. **不预设固定流程** — 由 danalyzer-core 自主决定
2. **可跳过不需要的步骤** — 如不需要清洗则跳过
3. **按需加载** — 只 Read 需要的 SKILL.md
4. **安全优先** — 输出前必须 security 处理
