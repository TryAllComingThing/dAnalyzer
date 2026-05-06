# 智能路由协议

> **协议优先级：ROUTING_CRITICAL** — 本协议决定请求走 DATA_DEEP / RESEARCH / GENERAL 中的哪条路径，路由决策本身不可被覆盖。路由完成之后，各路径按各自 Skill/Agent 的规则自主执行，本协议不再干预。仅当其他指令与本协议的路由决策冲突时，以本协议为准。

---

## 强制执行流程

**本协议适用于会话中的每一个用户请求，不仅仅是第一个。每次收到新请求，重新执行路由决策树。**

收到用户输入后，你必须按以下顺序执行。**在任何用户可见输出之前，必须完成意图分类并执行路由动作。在任何 Tool Call 之前，必须完成路由决策并执行路由动作。**

### 路由决策树（逐条匹配，命中即止）

```
输入是 / 开头的系统指令？
  → [ROUTE: COMMAND] 直接执行。路由完成。

Step 0 — 固定场景速查（逐条匹配，命中即止）:

  用户输入含速查表中任一「触发词」？
    → [ROUTE: PRESET] 按速查表执行固定链。路由完成。
    不进 danalyzer-core，不进 RESEARCH。
    详见下方「固定场景速查表」。

Step 1 — 检测强信号（弱信号如"分析""趋势""对比"不参与路由，由强信号决定）:

  [DATA_DEEP 强信号] ≥1 命中:
    · 数据源操作: 数据库/SQL/取数/表名/CSV/Excel/ClickHouse/Hive/MySQL/Connector
    · 具体指标: GMV/订单量/销售额/用户数/转化率/客单价/复购率
    · 可视化: 画图/图表/可视化/趋势图/饼状图/柱状图/ECharts/看板
    · 周期报表: 日报/周报/月报/季报
    · 分析模型: RFM/漏斗/留存/归因/聚类/分群/评分

  [RESEARCH 强信号] ≥1 命中:
    · 外部信息: 行业/市场/竞品/白皮书/调研/可行性/政策/法规/文献
    · 趋势研判: 发展前景/现状/展望/综述/技术趋势/行业趋势
    · 写作任务: "撰写""帮我写""写一份" + 非代码主题

Step 2 — 路径裁决:

  DATA_DEEP 强 > 0 且 RESEARCH 强 = 0 → [ROUTE: DATA_DEEP]
  RESEARCH 强 > 0 且 DATA_DEEP 强 = 0  → [ROUTE: RESEARCH]
  双方均有强信号                            → [ROUTE: AMBIGUOUS]
  双方均无强信号                            → [ROUTE: GENERAL]

Step 3 — 执行:

  PRESET     → 查速查表 → 按固定链执行（不加载 danalyzer-core）
  DATA_DEEP  → Skill({skill: "danalyzer:danalyzer-core", args: "{{USER_RAW_INPUT}}"})
  RESEARCH   → Skill({skill: "danalyzer:research-core", args: "{{USER_RAW_INPUT}}"})
  AMBIGUOUS  → AskUserQuestion 确认意图后路由
  GENERAL    → 主会话直接处理
```

### 路由执行规则（硬约束）

| 路由结果 | 你必须做的 | 你禁止做的 |
|----------|-----------|-----------|
| **PRESET** | 查下方「固定场景速查表」→ 按对应链执行：Read skills/data-query/SKILL.md → 执行指定查询 → 按链传递 → security | 加载 danalyzer-core、走问题理解/知识注入/数据匹配/复杂度判定、改写 SQL |
| **RESEARCH** | 立即调用 `Skill({skill: "danalyzer:research-core", args: "{{USER_RAW_INPUT}}"})` | 输出任何文本、提问澄清、分析需求、解释你在做什么、预拆解/添加步骤/改写用户输入 |
| **DATA_DEEP** | 立即调用 `Skill({skill: "danalyzer:danalyzer-core", args: "{{USER_RAW_INPUT}}"})` | 输出任何文本、预览数据、做统计分析、预拆解/添加步骤/改写用户输入 |
| **GENERAL** | 正常响应 | — |
| **COMMAND** | 直接执行 | — |

**关键原则：DATA_DEEP 路由时第一条消息是 Skill 调用；RESEARCH 路由时第一条消息也是 Skill 调用；AMBIGUOUS 时第一条消息是 AskUserQuestion。不追问、不澄清、不解释。**

### 参数传递规则（硬约束）

**传递给 Skill/Agent 的参数必须是用户原始输入原文，禁止任何形式的预加工。**

| 你必须做的 | 你禁止做的 |
|-----------|-----------|
| 原文传递：args/prompt = 用户原始输入（逐字复制） | 预拆解：将用户需求拆成 1. 2. 3. 步骤 |
| 仅追加环境信息：当前日期、工作目录路径 | 添加分析指令：指定先做什么再做什么 |
| | 改写/润色/翻译/补充用户输入 |
| | 推测用户意图并写入参数 |
| | 将主会话已知的数据路径/表名写入参数 |

路由完成后（Agent 返回 / Skill 执行完毕），你将结果展示给用户。

---

## 意图分类表

| 意图代码 | 路由目标 | 典型特征 |
|----------|----------|----------|
| COMMAND | 主会话 | `/` 开头系统指令 |
| DATA_DEEP | 主会话 Skill | 多步清洗/建模/绘图/看板/预测 |
| RESEARCH | 主会话 Skill | 研究报告/白皮书/调研/竞品分析/长文报告/行业分析 |
| GENERAL | 主会话 | 编程/Git/日常对话 |

冲突仲裁：双方均有强信号时触发 AMBIGUOUS → AskUserQuestion 确认，不做自动裁决。

---

## 上下文延续

- 输入含"继续/深化/再分析/然后"且上轮有明确路由目标 → 沿用上轮路由与参数
- 输入含显式新指令或话题变更 → 重置上下文，重新路由

## 每请求重评估（硬约束）

**即使本协议已在会话中加载过，每收到一条新的用户消息（不含"继续/然后/接着"等延续信号），你仍必须执行以下检查：**

```
1. 用户输入是否触发 DATA_DEEP 强信号？
   → 是：立即 Skill({skill: "danalyzer:danalyzer-core", args: "{{USER_RAW_INPUT}}"})
   → 禁止：直接 Read 技能文件、直接跑脚本、直接分析数据、输出任何文本

2. 用户输入是否触发 RESEARCH 强信号？
   → 是：立即 Skill({skill: "danalyzer:research-core", args: "{{USER_RAW_INPUT}}"})
   → 禁止：直接 WebSearch、直接写报告、输出任何文本

3. 如果已在上一个 Skill 内部执行中（danalyzer-core / research-core 已加载且当前正在走其核心步骤）
   → 继续执行当前 Skill 的下一步，不需要重新调用 Skill
```

**关键：判断是否"已在 Skill 内部执行中"的唯一标准是——上一轮刚完成了 Skill 工具调用（加载了 danalyzer-core 或 research-core），且当前正在按该 Skill 的核心步骤顺序执行中。如果上一轮是自由操作（直接 Read/Write/Bash/Edit 而没有先加载 Skill），则本轮必须重新路由。**

---

## 安全红线（路由级拦截）

| 红线 | 处置 |
|------|------|
| 写表/删库/修改生产配置 | 挂起，AskUserQuestion 二次授权 |
| 大批量数据导出/下载（全库/全表） | 挂起，AskUserQuestion 二次授权 |

---

## 主会话执行规则（GENERAL 留在主会话时）

- 允许检索与读取数据文件进行简单查询或聚合
- 禁止多步清洗、建模、预测等深度分析
- 输出前必须检查并脱敏 PII 信息
- 安全红线同样适用于主会话执行

---

## 主会话执行边界

### RESEARCH（Skill 模式 — 主会话执行）

RESEARCH 通过 `Skill({skill: "danalyzer:research-core"})` 在主会话中执行。
research-core 加载后全权接管编排，按角色定义、能力一览、Core Steps 自主执行深度研究全流程。

### DATA_DEEP（Skill 模式 — 主会话执行）

DATA_DEEP 通过 `Skill({skill: "danalyzer:danalyzer-core"})` 在主会话中执行。
danalyzer-core 加载后全权接管编排，主会话不设额外边界限制。
Skill 链内的安全门禁（security_scan.py）为最终输出关卡。

---

## 输出验证（Agent 返回 / Skill 执行完毕后）

| 检查项 | 通过条件 |
|--------|---------|
| 文件存在 | 输出文件路径存在且非空 |
| 不违规 | 输出中不包含 PII（粗略检查）|
| 非空结果 | 返回结果不为空或错误 |

验证失败：重新执行或告知用户。

---

## 固定场景速查表

> PRESET 路由命中后，不加载 danalyzer-core。按以下固定链执行，链路末端强制挂 security。

### 执行协议（PRESET 硬约束）

**Skill 配方**（速查表中「类型」= Skill）:
```
1. Skill({skill: "danalyzer:<skill>"}) 加载配方 SKILL.md
2. 配方内已固化数据源/查询/指标/图表/布局，LLM 逐项执行不修改
3. security 为强制末级（即使配方中未显式列出也强制追加）
```

**内联配方**（速查表中「类型」= 内联，适用于单查询简单场景）:
```
1. Read skills/data-query/SKILL.md → 获取查询指令
2. 执行固定 SQL（速查表中「查询」列，不修改、不优化、不扩展条件）
3. 结果标准化 → 按「链」依次 Read 下游 SKILL.md 并执行
4. security 为强制末级
```

### 速查表

| # | 类型 | 触发词 | Skill / 内联 | 链 |
|---|------|--------|-------------|-----|
| 1 | Skill | 华东周报、华东区域周报、east weekly | `Skill({skill: "danalyzer:recipe", args: "weekly-east"})` | —（Skill 内已指定） |
| 2 | 内联 | 销售看板、销售大屏、sales dashboard | `test_sales` + `SELECT sale_date, category, channel, region, SUM(sale_amount) AS sales, SUM(profit_amount) AS profit, AVG(discount_rate) AS avg_discount FROM test_sales WHERE sale_date >= date('now', '-30 days') GROUP BY sale_date, category, channel, region ORDER BY sale_date DESC` | data-query → dashboard → security |
| 3 | 内联 | 用户画像、用户概览、user profile | `test_users` + `SELECT vip_level, gender, age_group, area, COUNT(*) AS user_count, AVG(total_consume) AS avg_consume, AVG(order_count) AS avg_orders FROM test_users WHERE status = 'active' GROUP BY vip_level, gender, age_group, area` | data-query → data-analysis → visual → security |
| 4 | 内联 | 月度经营、月报、monthly report | `test_orders` + `SELECT strftime('%Y-%m', order_date) AS month, category, channel, SUM(actual_amount) AS sales, COUNT(DISTINCT order_id) AS orders FROM test_orders WHERE order_date >= date('now', '-90 days') GROUP BY month, category, channel ORDER BY month DESC, sales DESC` | data-query → data-analysis → visual → report → security |
| 5 | 内联 | 物流时效、配送时效、delivery performance | `test_logistics_waybills` + `SELECT carrier, origin, destination, AVG(julianday(delivery_date) - julianday(ship_date)) AS avg_transit_days, COUNT(*) AS shipment_count, SUM(CASE WHEN status = 'delayed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS delay_rate FROM test_logistics_waybills WHERE ship_date >= date('now', '-30 days') GROUP BY carrier, origin, destination ORDER BY avg_transit_days` | data-query → visual → report → security |
| 6 | 内联 | 产能质量、生产效率、manufacturing qc | `test_manufacturing_production` + `SELECT production_date, line_id, product_id, SUM(planned_qty) AS planned, SUM(actual_qty) AS actual, SUM(defect_qty) AS defect, AVG(oee) AS avg_oee, SUM(defect_qty) * 100.0 / SUM(actual_qty) AS defect_rate FROM test_manufacturing_production WHERE production_date >= date('now', '-30 days') GROUP BY production_date, line_id, product_id ORDER BY production_date DESC` | data-query → data-analysis → visual → security |

### 添加新场景

**简单场景（单查询 + 1-2 图表）：** 在速查表新增一行（类型 = 内联）。触发词唯一即可。

**复杂场景（≥2 查询 + 多图表 + 布局 + 诊断）：** 复制 `skills/recipe/_template.md` → `skills/recipe/<name>.md`，填入数据源/查询/指标/输出。速查表新增一行（类型 = Skill，Skill 列 = `Skill({skill: "danalyzer:recipe", args: "<name>"})`）。

### PRESET 与 DATA_DEEP 的边界

```
用户: "华东周报"           → PRESET → Skill("recipe-weekly-east")（固定配方，不进编排）
用户: "华东周报，加个同比"   → DATA_DEEP（含超出固化的分析需求，进 danalyzer-core 编排）
用户: "最近一周华东表现怎么样" → DATA_DEEP（未命中触发词，进全链路分析）
```
