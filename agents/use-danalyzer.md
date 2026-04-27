# use-danalyzer

---

<EXTREMELY-IMPORTANT>
如果你认为哪怕只有 1% 的可能性某个技能适用于你正在做的事情，你绝对必须调用该技能。

如果一个技能适用于你的任务，你没有选择。你必须使用它。

这不可协商。这不是可选的。你不能通过合理化来逃避。
</EXTREMELY-IMPORTANT>

---

## 检测规则

**触发条件**（满足任一即命中）:

| 信号 | 示例 |
|------|------|
| 数据查询意图 | "查询"、"取数"、"SQL"、"导出"、"统计"、"计算" |
| 分析意图 | "分析"、"趋势"、"对比"、"归因"、"漏斗"、"留存" |
| 建模意图 | "RFM"、"聚类"、"分群"、"预测"、"评分" |
| 报表意图 | "日报"、"周报"、"月报"、"看板"、"dashboard" |
| 可视化意图 | "画图"、"图表"、"可视化"、"趋势图"、 "饼状图"等图表|
| 数据源提及 | "数据库"、"ClickHouse"、"Hive"、"excel"、"csv"、"MySQL" 等数据库|

**排除条件**（不触发路由）:
- 纯代码/编程问题
- Git 操作、文件管理
- 与数据无关的系统运维

---

## 路由规则（按复杂度分流）

```
用户请求
    │
    ▼
评估: 是否命中检测规则？
    │
    ├── 是 → 判断复杂度
    │       │
    │       ├── 简单查询（单次取数，无组合）
    │       │   特征: "查询X"、"统计X"、"X是多少"、"计算X"
    │       │   路由: 直接 Skill (danalyzer:query:nl / danalyzer:data-query)
    │       │   约束: 结果需过 security
    │       │   开销: 零 Agent spawn
    │       │
    │       ├── 取数+展示（2个Skill组合）
    │       │   特征: "查询X并画图"、"导出X"
    │       │   路由: Skill 组合 (data-query → visual/export → security)
    │       │   开销: 无需 Agent
    │       │
    │       └── 分析/建模/报表（多Skill编排）
    │           特征: "分析"、"RFM"、"周报"、"看板"、"趋势"、"漏斗"
    │           路由: ⚠️ MANDATORY Agent: danalyzer:danalyzer-core
    │           原因: 需要需求拆解 + 任务规划 + 多Skill编排
    │           │
    │           └── danalyzer-core 内部:
    │                 ├── 需求理解 (内嵌)
    │                 ├── 需求拆解 (if 模糊 · 内嵌)
    │                 ├── 任务规划 (if 复杂 · 内嵌)
    │                 └── 按需加载 Skills → 执行
    │                      └── 异常? → error-handler (唯一 spawn)
    │
    └── 否 → 正常处理
```

## 复杂度判定速查

| 请求示例 | 判定 | 路由 |
|----------|------|------|
| "查询订单数量" | 简单查询 | `Skill: danalyzer:query:nl` |
| "上月GMV是多少" | 简单查询 | `Skill: danalyzer:data-query` |
| "统计各渠道用户数" | 简单查询 | `Skill: danalyzer:query:nl` |
| "查询销售趋势并画图" | 取数+展示 | data-query → visual |
| "导出用户数据为CSV" | 取数+展示 | data-query → export |
| "分析上个月销售趋势" | 分析 | `Agent: danalyzer:danalyzer-core` |
| "RFM用户分层" | 建模 | `Agent: danalyzer:danalyzer-core` |
| "生成Q1月报" | 报表 | `Agent: danalyzer:danalyzer-core` |
| "销售看板" | 看板 | `Agent: danalyzer:danalyzer-core` |
| "漏斗分析" | 分析 | `Agent: danalyzer:danalyzer-core` |

**不确定时**: 走 danalyzer-core（宁可多路由，不可漏路由）

## 关键约束

1. **简单查询直接走 Skill** — 不 spawn Agent，零开销
2. **多 Skill 编排必须走 danalyzer-core** — 需要拆解+规划+编排
3. **不确定时走 danalyzer-core** — 宁可多路由，不可漏路由
4. **用户透明** — 路由过程对用户无感
