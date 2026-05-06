---
name: danalyzer-core
description: 当用户在 dAnalyzer 系统中请求数据分析、查询、建模、报表或可视化时使用。不要用于编程、Git 操作或通用对话等非数据任务。
---

# dAnalyzer Core — 编排调度器

## ⛔ 加载方式自检（最先执行，不可跳过）

**本文件仅允许通过 `Skill({skill: "danalyzer:danalyzer-core"})` 加载。在读取任何后续内容之前，先验证加载方式：**

```
检查：当前上下文中，是否刚刚执行了 Skill 工具调用且 skill="danalyzer:danalyzer-core"？
  ├─ 是 → 继续执行 Section 零（路由自检）
  └─ 否 → 本文件是被手动 Read 或从系统提醒中回顾的，非当前请求的正确加载方式
           → 立即输出: [reroute: missing-core]
           → 立即终止，不执行任何数据分析操作
           → 不继续读取本文件后续内容
```

**如果本文件是作为之前 Skill 调用的系统提醒出现（而非当前请求的 Skill 加载），则判定为"否"。仅当当前用户消息的直接响应中包含 `Skill({skill: "danalyzer:danalyzer-core"})` 调用时，才判定为"是"。**

---

## Overview

dAnalyzer 数据分析系统的唯一编排入口。本 Skill 负责检测分析意图、理解分析问题、注入行业知识、按需匹配数据源、判定复杂度、路由到专用技能、管理执行链、并强制执行安全合规关卡。它不直接执行分析 — 而是委托给 data-query、data-clean、data-analysis、model、visual、report、dashboard、insight-gen、security 等子技能。

**设计原则：问题驱动，而非数据驱动。** 先理解用户想做什么分析、用什么方法、要什么输出，再去找数据、定链路。不因为"现有数据"限制分析思维。

## 何时使用

- **触发:** 用户消息含数据查询、分析、建模、报表或可视化意图（完整信号表见 Section 一）
- **不要用于:** 纯编程、Git 操作、运维或非数据类对话
- **不要用于:** 无数据维度的纯对话任务
- 不确定时：宁可激活，不可跳过

## 核心职责

- 检测并路由数据分析请求
- 理解分析问题（分析类型/方法/视角/输出形式，模糊时 AskUserQuestion）
- 注入行业知识（指标定义 + learn 修正）
- 按需匹配数据源（动态 > 数据库 > 本地文件，按分析需求定向查找）
- 按复杂度决策执行策略（简单快速通道 / 复杂完整编排）
- 按需编排技能链（选择哪些 Skills、什么顺序）
- 协调执行并返回结果
- 技能异常时按策略表自行处理（见 Section 七）

**技能编排参考表、分析类型决策、图表选型见 `analysis.md`（按需读取）。**

---

## 核心步骤

0. **路由自检** — 加载后首件事：检查请求是否真正属于数据分析范畴。若明显属于深度研究（行业调研/竞品分析/政策解读/白皮书）且不涉及本地数据操作，输出 `[reroute: research]` 并终止。若不属于任何分析场景（纯编程/Git），输出 `[reroute: general]` 并终止。→ 详见「零、路由自检」
1. **检测意图** — 从用户消息匹配分析/查询/建模/报表/可视化信号 → 详见「一、检测规则」
2. **问题理解** — 判定分析类型、方法、视角、输出形式。模糊时调用 `AskUserQuestion`（围绕分析意图，而非数据源）→ 详见「二、问题理解」
2.5. **行业判定** — 判定行业归属 → 详见「二点五、行业判定」
3. **知识注入** — 非简单查询时强制执行：获取行业动态注册表 → 输出结构化 plan JSON → 运行 `retrieve_context.py`（行业指标 + learn 修正）→ 详见「三、知识注入」
4. **数据匹配** — 根据分析需求按优先级定向查找：动态文件 > 数据库 > 本地注册文件 → 详见「四、数据匹配」
5. **复杂度判定** — 简单（≤2 skills）走快速通道，复杂先出计划再执行 → 详见「五、复杂度判定」
6. **技能链执行** — 按序 Read 各 skill SKILL.md 并执行 → 详见「六、执行纪律规则」和「九、调用协议」
7. **安全门禁** — 所有输出经 `security_scan.py` 扫描 → 详见「八、安全规范」
8. **返回结果** — 交付脱敏后的完整结果

---

## 零、路由自检

> 对应 核心步骤 第 0 步 — 路由协议的安全阀，允许本 Skill 在明显误判时自救。

本 Skill 被路由协议加载后，**首件事是验证当前请求是否真正属于数据分析范畴**。不依赖路由协议永远正确，本 Skill 保留自检权。

### 判断逻辑

| 条件 | 判定 | 动作 |
|------|------|------|
| 请求含本地数据操作信号（SQL/取数/CSV/Excel/Connector/表名）+ 具体指标（GMV/订单量/销售额...） | 属于数据分析 | 继续执行 |
| 请求仅含外部研究信号（行业调研/竞品分析/政策解读/白皮书/文献综述/技术趋势）且无本地数据操作 | 不属于数据分析 | 输出 `[reroute: research]` 并终止 |
| 请求不涉及任何数据操作或研究（纯编程/Git/日常对话） | 不属于数据分析 | 输出 `[reroute: general]` 并终止 |
| 无法确定 | 继续执行，由后续 Steps 澄清 | — |

### Reroute 输出格式

```
[reroute: research]    ← 应走深度研究路径
[reroute: general]      ← 应走通用对话路径
```

输出 Reroute 信号后**立即终止，不继续执行任何分析步骤**。主会话收到 Reroute 信号后重新路由到正确路径。

---

## 一、检测规则

> 对应 核心步骤 第 1 步

**触发条件**（满足任一即激活本 Skill）：

| 信号 | 示例 |
|------|------|
| 数据查询意图 | "查询"、"取数"、"SQL"、"导出"、"统计"、"计算" |
| 分析意图 | "分析"、"趋势"、"对比"、"归因"、"漏斗"、"留存" |
| 建模意图 | "RFM"、"聚类"、"分群"、"预测"、"评分" |
| 报表意图 | "日报"、"周报"、"月报"、"报告生成"、"对比报告" |
| 可视化意图 | "画图"、"图表"、"可视化"、"趋势图"、"饼状图" |
| 数据源提及 | "数据库"、"ClickHouse"、"Hive"、"excel"、"csv"、"MySQL" |

**排除条件**：纯编程/Git/运维/日常对话等非数据类请求。

**不确定时**：宁可激活，不可跳过。

---

## 二、问题理解

> 对应 核心步骤 第 2 步 — 先理解分析问题，后匹配数据。问题驱动，而非数据驱动。

### 2.1 分析问题拆解

收到请求后，从以下 4 个维度理解用户的真实分析意图：

| 维度 | 说明 | 示例 |
|------|------|------|
| **分析类型** | 描述性/诊断性/预测性/规范性/探索性 | "为什么销售下降" → 诊断性 |
| **分析方法** | 趋势/对比/占比/排名/归因/漏斗/留存/异常/相关性/聚类/RFM | "各渠道对比" → 对比分析 |
| **分析视角** | 时间变化/结构分布/分组对比/关联与异常 | "按月份和区域看" → 时间变化 + 分组对比 |
| **输出形式** | 看板/可视化图表/数据表格/文字报告/两者都要 | "画个趋势图" → 可视化 |

### 2.2 模糊判断标准

满足任一即判定为"需求模糊"，必须向用户澄清：

| 判断条件 | 示例 |
|---------|------|
| 缺少分析类型 | "看下数据"（描述？诊断？预测？） |
| 缺少分析方法 | "分析销售"（趋势？占比？对比？归因？） |
| 缺少分析视角 | "分析用户"（按时间？区域？渠道？分层？） |
| 缺少输出形式 | "分析下数据"（要图表？报告？表格？看板？） |
| 多重解释可能 | "分析产品"（指销量、评价还是库存？） |

### 2.3 澄清方式

**必须调用 AskUserQuestion，不得用纯文本出选项。**

每个 question 对应一个澄清维度，header 用 ≤6 字中文标签。可多选时设 `multiSelect: true`。

**格式要求**：
- 仅对模糊维度提问，不凑数（通常 2~3 个 question）
- options 围绕**分析意图**（类型/方法/维度/输出），而非数据源
- 数据源在后续「数据匹配」步骤中按需自动发现，不在此阶段暴露给用户
- 每个 option 的 label 简洁（≤40 字），description 说明用途

```
AskUserQuestion({
  questions: [
    {
      question: "想从哪个角度分析？",
      header: "分析类型",
      multiSelect: false,
      options: [
        {label: "趋势分析", description: "数据随时间的变化走向"},
        {label: "对比分析", description: "不同分组之间的差异"},
        {label: "占比分析", description: "各部分在整体中的比重"},
        {label: "归因分析", description: "找出导致变化的关键因素"}
      ]
    },
    {
      question: "想从哪些视角观察？（可多选）",
      header: "分析视角",
      multiSelect: true,
      options: [
        {label: "时间变化", description: "走势、拐点、周期性、环比同比"},
        {label: "结构分布", description: "构成、占比、集中度、头部/长尾"},
        {label: "分组对比", description: "不同组之间的差异与排名"},
        {label: "关联与异常", description: "变量间的关联、因果线索与异常发现"}
      ]
    },
    {
      question: "偏好什么输出形式？",
      header: "输出形式",
      multiSelect: false,
      options: [
        {label: "HTML 可视化看板", description: "ECharts 交互图表 + KPI 卡片"},
        {label: "文字分析报告", description: "数据表格 + 洞察 + 建议"},
        {label: "两者都要", description: "HTML 看板 + Markdown 报告"}
      ]
    }
  ]
})
```

> **分析视角说明：** 视角选项是泛化的分析透镜，不与任何数据字段绑定。选定视角后，在 Step 4（数据匹配）阶段按需查找具体维度字段。例如"分组对比"视角可能匹配到数据源中的品类列、渠道列或区域列——哪个字段存在就用哪个，字段缺失则跳过对应维度。

### 2.4 分析指引场景（意图明确，执行阶段澄清）

以下场景意图已明确为 DATA_DEEP，不在问题理解阶段触发澄清，在执行阶段按对应方式主动澄清后继续：

| 场景 | 判定信号 | 处理方式 |
|------|----------|----------|
| 预测无历史 | 要求预测/预估，但未提供历史数据范围 | 先反问确认回溯窗口和时间粒度，确认后继续 |
| 指标未定义 | 指标有多个业务口径（如"活跃度"→ DAU/MAU/WAU，"产能利用率"→ 时间利用率/性能利用率/质量利用率） | 列出可选口径让用户选择 |
| 大范围分析 | 时间跨度极大或数据量巨大（全量/多年） | 建议缩小范围或抽样策略，用户确认后执行 |
| 伪分析 | 无数据或仅片段数据但要求深度分析 | 说明数据局限性，按有限数据做分析或引导补充数据 |

这些场景在执行阶段触发澄清，而非问题理解阶段。

---

## 二点五、行业判定

> 对应 核心步骤 第 2 步与第 3 步之间 — 问题理解完成后，知识注入之前，必须先判定行业。不可跳过。

问题理解阶段澄清了**分析视角**（时间变化/结构分布/分组对比/关联与异常），但尚未确定具体分析哪些指标、用哪个行业的定义体系。本步骤完成行业归属判定。**指标扩展延后到 Step 3b**（获取 context-card 后，基于真实 indicator_code 做映射，避免凭空猜测）。

### Step 2.5: 行业判定

从用户原始输入中提取行业信号词，按以下优先级判定行业：

| 优先级 | 信号来源 | 示例 |
|--------|---------|------|
| 1 | 用户显式指定行业 | "分析快消订单"、"看制造业产能" |
| 2 | 用户问题含行业特征词 | "GMV/订单量/客单价" → fmcg、"OEE/不良品率" → manufacturing |
| 3 | 数据源 schema_hint 的 industry 字段 | datasources.yaml 中数据源标注的行业标签 |
| 4 | 默认行业 | fmcg（最通用） |

**禁止行为：** 跳过行业判定直接进入知识注入。即使最终落到了默认行业，也必须显式记录判定路径。

**产出：** 行业 code（如 `fmcg`、`manufacturing`），传入 Step 3a 定向拉取 context-card。指标扩展在 Step 3b 基于 context-card 的真实 indicator_code 完成。

---

## 三、知识注入

> 对应 核心步骤 第 3 步 — 在理解问题之后、匹配数据之前，注入行业知识和 learn 修正。

### 触发条件

| 查询复杂度 | 触发规则 |
|-----------|----------|
| 简单查询（"查询订单数量"、"上月GMV"） | 可跳过，指标明确无需检索 |
| 中等/复杂（含分析/建模/报表/可视化意图） | **强制执行**，不可跳过 |
| 含行业特征词（"配送时效"、"销售额"、"产能利用率"等） | **强制执行**，即使查询简单 |

判断标准：若后续复杂度判定为中等或复杂，则知识注入为强制步骤。

### Step 3a: 定向拉取注册表

**使用 Step 2.5 判定的行业，定向拉取，不拉全量：**

```bash
# 定向拉取（默认）
python3 scripts/registry_scanner.py --format context-card --industry <2.5a结果>

# 仅当 Step 2.5 置信度 < 0.4 时，退化为全量
python3 scripts/registry_scanner.py --format context-card
```

### Step 3b: 指标扩展

> **此时 context-card 已就绪** — Step 3a 返回了该行业的真实 `indicators` 和 `scenarios` 列表。基于真实 code 做视角→指标映射，不凭空猜测。

分析视角是泛化的，需要映射到行业的具体指标。映射规则：

| 分析视角 | 自动扩展的指标类型 | 扩展逻辑 |
|----------|-------------------|---------|
| 时间变化 | 核心量值指标 + 环比/同比 | 从 context-card indicators 中选取含 `amount`/`volume`/`count` 的量值型指标 |
| 结构分布 | 占比指标 + 集中度指标 | 从 context-card indicators 中选取量值指标 + 带 `_share`/`_rate` 后缀的占比型指标 |
| 分组对比 | 多维度指标 + 排名 | 选取所有量值指标，标注 `BY <可用维度>` 分组 |
| 关联与异常 | 相关性指标 + 异常检测 | 选取所有数值型指标，标注 IQR/Z-score 异常扫描 |

**扩展流程：**
1. 从 Step 3a 的 context-card 输出中提取 `indicators` 列表（真实的 indicator_code）
2. 根据用户选定的分析视角，按上述规则筛选/组合指标
3. 合并去重，形成完整的 indicators 清单
4. 将此清单传入 Step 3d（plan JSON）

> **设计要点：** 用户选的是"结构分布"视角，不指定品类还是渠道。哪些维度可用，由 Step 4（数据匹配）中的实际数据字段决定。指标扩展只负责把"视角→指标"的映射做对，维度绑定留给数据匹配。

### Step 3c: 行业知识兜底（三级降级，强制）

Step 3a 定向拉取后，**必须检查返回值中是否实际包含 indicators/scenarios**。若无，按以下逐级降级：

```
retrieve_context 返回值检查:
  ├── indicators 非空 且 scenarios 非空
  │     → 正常注入。knowledge_source = "industry_direct"
  │
  ├── indicators 非空 但 scenarios 为空
  │     → 兜底 1: 场景从相邻行业或通用模板补充
  │       knowledge_source = "fallback_partial"
  │
  ├── indicators 为空（行业目录不存在或为空）
  │     → 兜底 2: 降级到默认行业 fmcg
  │       registry_scanner.py --industry fmcg
  │       报告中标注「行业知识缺失，使用默认行业指标 fmcg」
  │       knowledge_source = "fallback_fmcg"
  │
  └── fmcg 也拉不到
        → 兜底 3: 退化到数据 Schema
          不使用知识库指标，直接用数据源的列名做指标
          报告中标注「无行业知识注入，仅基于数据 Schema」
          knowledge_source = "fallback_schema"
```

**兜底字段规则：**

| knowledge_source | 含义 | 用户感知 |
|-----------------|------|---------|
| `industry_direct` | 行业知识直接命中 | 无感知 |
| `fallback_partial` | 部分命中，场景从通用模板补充 | 无感知 |
| `fallback_fmcg` | 行业缺失，降级为快消指标 | 告知用户 |
| `fallback_schema` | 完全无知识，退化到数据 Schema | 显式警告 |

### Step 3d: 输出分析计划 JSON

根据兜底后的实际 indicators/scenarios 填写。**严格 JSON，无额外文字**。必须包含 `knowledge_source` 和 `fallback_reason` 字段：

```json
{
  "industry": "fmcg",
  "intent_id": "sales_diagnostic",
  "analysis_type": "diagnostic",
  "confidence": 0.9,
  "indicators": ["sales_amount", "order_count"],
  "scenarios": ["sales_trend"],
  "models": ["attribution-model"],
  "dimensions": ["time", "category"],
  "skill_chain": ["data-query", "data-clean", "data-analysis", "model", "visual", "report", "security"],
  "knowledge_source": "industry_direct",
  "fallback_reason": null,
  "reasoning": "用户问品类表现不好的原因，属于诊断性分析，需归因模型"
}
```

**多行业示例**（indicators 和 scenarios 必须来自 context-card，以下仅为示意）：

| 行业 | 典型 query | indicators | scenarios | models |
|------|----------|-----------|----------|--------|
| 快消 (fmcg) | "品类表现不好的原因" | sales_amount, order_count | sales_trend | attribution-model |
| 制造 (manufacturing) | "产能利用率下降原因" | capacity_rate, defect_rate, downtime_hours | production_quality | correlation-analysis |
| 物流 (logistics) | "配送时效对比分析" | delivery_ontime_rate, avg_transit_days, cost_per_order | delivery_efficiency | trend-analysis |
| 金融 (finance) | "用户信用评分分布" | credit_score, overdue_rate, loan_amount | risk_assessment | clustering |

**字段填值规则**：

| 字段 | 规则 |
|------|------|
| `industry` | **直接使用 Step 2.5 的判定结果**，非 context-card 中重新匹配 |
| `intent_id` | 从 `knowledge/intent-routing.yaml` 的 `intents` 中匹配 `keywords` 最相关的一项 |
| `analysis_type` | 从匹配到的 intent 取，或自行判断：descriptive / diagnostic / predictive / prescriptive / exploratory |
| `confidence` | 自评 0.0-1.0 |
| `knowledge_source` | **必填。** `industry_direct` / `fallback_partial` / `fallback_fmcg` / `fallback_schema` |
| `fallback_reason` | 当 knowledge_source ≠ `industry_direct` 时**必填**，说明降级原因 |
| `indicators` | **必须使用 context-card 中存在的 indicator_code**，至少 2 个 |
| `scenarios` | **必须使用 context-card 中存在的 scenario_code**，至少 1 个 |
| `models` | 参考 intent 的 `models` |
| `dimensions` | 来自问题理解阶段的分析视角拆解（如"时间变化+分组对比"→ `["time", "group_compare"]`），具体维度字段在 Step 4 数据匹配后填入 |
| `skill_chain` | 参考 context-card 底部的 `analysis_type → skill_chain` 映射 |

### Step 3e: 执行检索

**显式传 `--industry`，不依赖自动检测：**

```bash
python3 scripts/retrieve_context.py \
  --query "<原始查询>" \
  --industry <2.5a结果> \
  --plan '<上述JSON>'
```

`--industry` 从 Step 2.5 直传，保证行业判定的一贯性。不依赖脚本内自动检测。

### 兜底保证

该命令内部走 L1 精确查询 → L2 FTS 模糊搜索 → L3 LLM 推理的三级兜底。
即使 Step 3c 的 JSON 中有个别 code 拼错，校验层自动过滤 + 场景反查补齐。JSON 完全写错时 L2 接住。

**行业知识缺失时**，Step 3c 已在 plan JSON 中记录了 `knowledge_source` 和 `fallback_reason`，
下游 skill（如 insight-gen、report）**必须检查这两个字段**，在输出中显式告知用户知识来源级别。

> **设计要点：** `registry_scanner.py` 动态扫描文件系统，新增行业/指标/场景**零配置**自动可用。LLM 始终拿到最新的 code 列表，从源头消除幻觉。

---

## 四、数据匹配

> 对应 核心步骤 第 4 步 — 根据分析需求按优先级定向匹配数据源，不做无条件的全量扫描。

**核心原则：按需匹配，优先级明确。** 动态文件 > 数据库 > 本地注册文件。

### Step 4a: 推导数据需求

从知识注入阶段的 plan JSON（`indicators`、`dimensions`）推导需要的数据类型和字段。例如：
- `sales_amount` + `time` → 需要含日期和金额的销售数据
- `order_count` + `channel` → 需要含渠道和订单量的数据

### Step 4b: 按优先级匹配

**优先级 1 — 动态文件发现**（最高优先级，用户可能临时放入新数据）：

从 `connectors/datasources.yaml` 提取 `file_discovery.search_paths` 和 `file_discovery.extensions`，**动态构建扫描命令**（禁止硬编码路径或扩展名）：

```
# 从 yaml 提取: search_paths → paths, extensions keys → exts
# 动态构建: ls -lh {path}/*.{ext} 2>/dev/null
```

记录文件名 + 文件大小 (`ls -lh`)。匹配文件名/扩展名与数据需求的关联度。

**优先级 2 — 数据库**（结构化数据，schema 明确）：

读取 `connectors/datasources.yaml` 的 `databases` 段。校验连通性（可用 `python connectors/datawarehouse/mysql.py --test <db_name>` 或类似方式）。匹配 `schema_hint` 中的表名和字段与数据需求的关联度。

**优先级 3 — 本地注册文件**（预置数据，已知 schema）：

读取 `connectors/datasources.yaml` 的 `files` 段。匹配 `schema_hint` 中的字段与数据需求的关联度。

### Step 4c: 汇总匹配结果

综合三层匹配结果，形成**与当前分析需求关联的数据源清单**。不列出全量数据源，仅列出相关的。

### 结果判断

- 匹配到相关数据源 → 进入复杂度判定
- 数据源全部为空（databases / files / 扫描结果）→ 报告「当前无可用数据源」并终止
- 有数据源但无与当前分析需求匹配的 → 报告「未找到匹配的数据源」，列出可用的数据源供用户参考

---

## 五、复杂度判定

> 对应 核心步骤 第 5 步

| 请求示例 | 判定 | 处理方式 |
|----------|------|----------|
| "查询订单数量" | 简单 | 快速通道：data-query → security |
| "上月GMV" | 简单 | 快速通道：data-query → security |
| "各渠道用户数" | 简单 | 快速通道：data-query → security |
| "查询销售趋势并画图" | 中等 | 完整流程（含知识注入） |
| "分析上个月销售趋势" | 复杂 | 问题理解 → 知识注入 → 数据匹配 → 多技能编排 |
| "RFM用户分层" | 复杂 | 问题理解 → 知识注入 → 数据匹配 → 多技能编排 |
| "生成Q1月报" | 复杂 | 问题理解 → 知识注入 → 数据匹配 → 多技能编排 |
| "销售看板" | 复杂 | 问题理解 → 知识注入 → 数据匹配 → 多技能编排 |
| "漏斗分析" | 复杂 | 问题理解 → 知识注入 → 数据匹配 → 多技能编排 |

### 决策规则表

| 需求明确？ | 任务复杂？ | 动作 |
|-----------|-----------|------|
| 明确 | 简单（≤2 技能） | 快速通道：跳过问题理解和知识注入，直接 data-query → security |
| 明确 | 复杂（>2 技能或有依赖） | 完整流程：知识注入 → 数据匹配 → 给出执行计划 → 执行 |
| 模糊 | 简单 | 先澄清需求（问题理解），再走快速通道 |
| 模糊 | 复杂 | 先澄清需求（问题理解），再走完整流程 |

---

## 六、执行纪律规则

> 对应 核心步骤 第 6 步

| 规则 | 说明 |
|------|------|
| Skill 规则优先 | SKILL.md 中定义的标准/公式/评分规则优先级高于通用知识 |
| 子技能必须加载 | Skill 包含子技能文件时（如 references/rfm-analysis.md），必须读取对应文件 |
| 禁止跳过 Skill | 存在对应 Skill 时禁止用自身知识替代执行 |
| 数据 I/O 用 Connector | 禁止手写 csv/json 读写，统一使用 connectors/ 接口 |

---

## 七、错误处理

```
错误发生 → 判断错误类型 → 匹配策略 → 执行
```

### 错误类型与处理决策

| 错误类型 | 严重程度 | 默认策略 | 可选策略 |
|----------|----------|----------|----------|
| 取数超时 | 可恢复 | 重试（最多3次，指数退避 1s→2s→4s） | 跳过、降级 |
| 数据为空 | 警告 | 跳过（记录警告，继续下一个技能） | 中止 |
| 格式错误 | 可恢复 | 重试（1次） | 跳过、中止 |
| 权限不足 | 致命 | 中止任务，报告错误 | - |
| 规则违规 | 致命 | 中止任务，报告错误 | - |
| 资源不足 | 可恢复 | 重试（2次） | 降级、中止 |
| 未知错误 | 可恢复 | 重试（1次） | 中止 |

### 策略说明

| 决策 | 说明 | 执行是否继续 |
|------|------|-------------|
| **retry** | 重试当前技能 | 重试成功则继续 |
| **skip** | 跳过当前技能，进入下一个 | 是 |
| **degrade** | 使用简化逻辑或备用数据源 | 是 |
| **abort** | 中止整个任务 | 否 |

### 异常处理原则

- 临时性错误（超时、网络）优先重试，不轻易中止
- 合规/权限错误必须中止，不可重试或跳过
- 可降级时不中止，保证部分结果交付
- 策略表未覆盖的边缘情况：默认 degrade，交付已完成的部分结果，不 spawn 新 Agent

### 技能链中断恢复（断点续传）

中间技能失败时，不丢弃已完成步骤的成果。按以下规则恢复：

**恢复策略：**

| 失败位置 | 已完成步骤 | 恢复动作 |
|---------|-----------|---------|
| data-clean 失败 | data-query 已完成 | 保留查询结果 JSON，修复清洗逻辑后从 data-clean 重试 |
| data-analysis 失败 | data-query + data-clean 已完成 | 保留清洗后数据，调整分析方法后从 data-analysis 重试 |
| model 失败 | data-query + data-clean + data-analysis 已完成 | 保留分析结果，更换模型或降级为 data-analysis 深度报告 |
| visual 失败 | 数据准备已全部完成 | 保留分析结果，降级为纯文字 report 输出 |
| dashboard 失败 | 数据准备已全部完成 | 保留分析结果，降级为多个独立 visual 图表 |
| security 失败 (P0) | 全部上游已完成 | 移除敏感字段，从 security 重新扫描 |

**断点续传规则：**

1. **已完成结果不丢弃** — 每个技能输出写入 `output/` 目录作为检查点，后续技能失败时已保存的结果直接复用
2. **最多恢复 2 次** — 同一技能失败 2 次后不再重试，降级或跳过
3. **降级不降质** — 降级时向用户说明「原计划 X → 因 Y 失败，降级为 Z」，提供降级后的最大可用结果
4. **用户可见恢复** — 恢复时告知用户：「[技能名] 失败：[原因]。已完成 [N]/[M] 步骤，从断点继续」
5. **恢复上限** — 整个技能链中断恢复不超过 3 次，超过则交付已完成部分 + 未完成清单

**快速通道恢复**（简单查询，≤2 技能）：
- data-query 失败 → 重试 1 次，仍失败则报告「数据源不可用」
- security 失败 → 脱敏后重新扫描，P0 命中则中止

---

## 八、安全规范

> 对应 核心步骤 第 7 步

所有输出链路末尾强制嵌入 security 处理：

```
输出流程: ... → 输出技能 → security → 最终输出
                              ↑
                      脱敏 + 合规检查（强制）
```

**禁止行为**：
- 导出未脱敏的 PII 数据
- 绕过 security 直接输出
- 记录敏感信息到日志

---

## 九、调用协议（资产路径与加载方式）

> 对应 核心步骤 第 6 步

### 技能加载

技能是通过 Read 文件加载的。按需 Read 以下路径获取具体指令：

| 技能 | 主文件 | 子技能 |
|------|--------|--------|
| context-retriever | `skills/context-retriever/SKILL.md` | - |
| data-query | `skills/data-query/SKILL.md` | - |
| data-clean | `skills/data-clean/SKILL.md` | `skills/data-clean/references/null-handling.md`, `references/deduplication.md`, `references/format.md`, `references/outlier.md`, `references/text-cleaning.md` |
| data-quality-check | `skills/data-quality-check/SKILL.md` | - |
| data-analysis | `skills/data-analysis/SKILL.md` | - |
| model | `skills/model/SKILL.md` | `skills/model/references/rfm-analysis.md`, `references/funnel-analysis.md`, `references/forecasting.md`, `references/cohort-analysis.md`, `references/clustering.md`, `references/attribution.md`, `references/correlation-analysis.md`, `references/trend-analysis.md` |
| visual | `skills/visual/SKILL.md` | `skills/visual/references/chart-standard.md`, `skills/visual/assets/page-chrome.html`, `skills/visual/assets/export-template.md` |
| report | `skills/report/SKILL.md` | `skills/report/assets/report-template.md`, `skills/report/references/comparison-report.md` |
| dashboard | `skills/dashboard/SKILL.md` | - |
| security | `skills/security/SKILL.md` | `skills/security/references/sensitive-detection.md`, `references/desensitize.md`, `references/pii-detection.md`, `references/masking-engine.md`, `references/masking-rules.md`, `references/compliance-check.md`, `references/audit-log-gen.md` |
| insight-gen | `skills/insight-gen/SKILL.md` | - |

**加载规则**：单个技能链中，每个技能的主文件 Read 1 次，子技能按需 Read。

### 技能间数据契约（输入前置条件）

编排调度时，**调用下游技能前必须校验上游输出满足下游的输入契约**。不满足则中止或降级，不得将不合格数据传入下一技能。

| 技能 | 需要的前置输入 | 上游提供者 | 校验规则 |
|------|-------------|-----------|---------|
| data-query | 注册数据源名称 + 查询条件（SQL 或自然语言） | danalyzer-core 数据匹配结果 | 数据源在 `datasources.yaml` 中已注册；查询为只读 |
| data-clean | `{columns, rows, row_count, source}` 格式数据 | data-query | rows 非空；至少含 1 个可清洗字段 |
| data-quality-check | 清洗后的数据（同上格式） | data-clean | 数据含明细行（非仅有汇总）；至少 1 个维度可评估 |
| data-analysis | 已清洗的结构化数据 | data-clean 或 data-query | 非空数据集；至少 1 个数值字段；样本量 ≥ 1 |
| model | 已清洗的结构化数据 + 明确的建模目标 | data-clean 或 data-query | 数据量 ≥ 模型最小要求（如聚类 ≥ 100 行、RFM ≥ 500 行）；含必要字段 |
| visual | 分析结果数据（统计量/模型输出）+ 图表类型意图 | data-analysis / model / data-query | 数据非空；图表类型与数据维度兼容 |
| dashboard | 多组分析结果数据（KPI + 图数据 + 明细） | data-analysis / model | 至少 1 个 KPI + 1 个图表数据源；数据来源一致 |
| report | 分析结论 + 数据附件 + 报告类型 | data-analysis / model | 分析已完成；报告类型与数据粒度匹配 |
| insight-gen | 统计指标 + 效应量 + 样本量信息 | data-analysis / model | 统计指标非空；效应量（d/r/百分比）可用 |
| security | 待输出数据（任意格式） | 所有输出技能 | 数据已格式化，非中间计算状态 |
| context-retriever | 分析 plan JSON 或行业关键词 | danalyzer-core Step 3b | plan JSON 含 `indicators` 和 `industry` 字段 |

**契约校验失败处理**：
- 上游数据为空 → 中止当前技能，记录警告，不继续传递空数据
- 上游格式不匹配 → 尝试格式转换（如 rows 从 `list[dict]` → `list[list]`），转换失败则中止
- 上游缺少必要字段 → 降级：跳过该技能，标记输出不完整
- 数据量不达标 → 警告用户并标注局限性，继续执行

### 脚本调用

| 用途 | 命令 |
|------|------|
| 行业上下文检索 | `python3 scripts/retrieve_context.py --query "<关键词>" --industry <行业>` |
| 数据查询执行 | `python3 scripts/execute_query.py --sql "<SQL>"` |
| 安全脱敏扫描 | `python3 scripts/security_scan.py --stdin`（管道输入）或 `--file <path>` |
| 指标报告生成 | `python3 scripts/generate_metrics_report.py --industry <行业>` |

所有脚本在 `scripts/` 目录下，项目根目录执行。

### 行业数据检索

数据在 `knowledge/industry/<行业>/` 目录：

```
knowledge/industry/
└── fmcg/           # 快消（8 指标 + 4 场景 + 字段映射）
```

每个行业的 `.db` 文件由 IndustryStore 自动同步生成，通过 `python3 scripts/retrieve_context.py` 统一检索。

### 完整执行链路

本文件由主会话通过 `Skill({skill: "danalyzer:danalyzer-core"})` 加载。加载后按以下链路在主会话中编排执行：

```
Skill 加载 → 按以下链路执行:
  │
  ├─ [Step 0] 路由自检 → 验证请求属于数据分析范畴（含 Reroute 逃生舱）
  ├─ [Step 1] 检测意图 → 匹配分析/查询/建模/报表/可视化信号
  ├─ [Step 2] 问题理解 → 分析类型/方法/视角/输出形式 + AskUserQuestion（模糊时）
  ├─ [Step 2.5] 行业判定 → 行业归属判定
  ├─ [Step 3] 知识注入 → registry_scanner.py → 指标扩展 → 兜底检查 → plan JSON → retrieve_context.py（非简单时强制）
  ├─ [Step 4] 数据匹配 → 按需定向查找：动态文件 > 数据库 > 本地注册文件
  ├─ [Step 5] 复杂度判定 → 简单走快速通道 / 复杂走完整流程
  ├─ [Step 6] 逐技能执行：
  │   ├─ 按技能加载表 Read skills/<skill>/SKILL.md → 获取具体指令
  │   ├─ Read 子技能文件（如有）
  │   └─ 必要时查 rules/ 规则文件
  ├─ [Step 7] 安全门禁 → python3 scripts/security_scan.py（强制）
  └─ [Step 8] 返回结果
```

---

## 十、分析思维链

每次分析请求按以下框架思考（不影响操作流程，操作流程由本文件 Sections 0-9 决定）：

```
Step 1: 理解需求
  - 用户真正想知道的业务问题是什么？
  - 有什么特殊要求或前提假设？

Step 2: 设计分析
  - 需要哪些指标？什么维度对比？
  - 时间范围和粒度？需要什么分组？

Step 3: 解读数据
  - 数据说明了什么业务问题？
  - 有什么显著变化、异常或亮点？

Step 4: 给出洞察
  - 对业务的含义是什么？
  - 建议采取什么行动？还有什么可深入分析？
```

---

## 十一、分析偏好

### 分析模式

| 分析模式 | 说明 | 默认 |
|----------|------|------|
| 趋势分析 | 数据随时间变化 | ✅ |
| 对比分析 | 环比/同比/区域等维度差异 | ✅ |
| 占比分析 | 各部分占比结构 | ✅ |
| 排名分析 | Top N 排序 | ✅ |
| 转化分析 | 漏斗各环节转化率 | ✅ |
| 异常检测 | 显著偏离的数据点 | ✅ |
| 相关性分析 | 变量间关系 | ❌ 按需开启 |

### 洞察深度

| 级别 | 说明 | 适用场景 |
|------|------|----------|
| 基础 | 快速结论 | 简单查询、单次取数 |
| 标准 | 数据 + 结论 + 洞察 | 日常分析（默认） |
| 深度 | 完整报告 + 建议 | 专项分析、月报、决策支持 |

---

## 常见借口与纠正

| 借口 | 现实 |
|--------|---------|
| "这个查询很简单，我凭记忆写 SQL 就行" | Schema 可能已变更；必须用 `--schema` 获取真实表结构 |
| "用户的意图很明确了" | 模糊需求跳过澄清导致错误分析的概率极高 |
| "这个输出没有敏感数据，跳过安全扫描" | 安全扫描是所有输出的强制关卡，不可跳过 |
| "先扫一遍数据源，看看有什么数据再说" | 数据驱动而非问题驱动 — 应反过来：先理解问题，再按需匹配数据 |

## 红线

- **未授权 PII:** 用户请求涉及 PII 或敏感数据但无明确授权范围 — 停止并澄清
- **数据源匹配失败:** 所有数据源匹配对分析需求返回空 — 不可使用过期 schema 继续
- **澄清被绕过:** 模糊请求未澄清 — 输出可能错误，重新开始澄清
- **CRITICAL 安全命中:** security 扫描返回 CRITICAL（P0 命中）— 立即中止
- **致命技能错误:** 技能链中任一技能返回致命错误（权限不足、规则违规）— 不可重试或跳过
- **数据驱动思维:** 基于可用数据而非用户问题选择分析方法 — 违反设计原则

## 验证

1. 验证路由自检已完成：确认请求已被验证为数据分析范畴
2. 验证问题理解已完成：确认分析类型、方法、视角、输出形式均已识别
3. 验证模糊请求已澄清：确认已通过 AskUserQuestion 向用户确认
4. 验证行业判定已完成：确认 Step 2.5 已判定行业 code，非空且记录判定路径（优先级 1-4 之一）
5. 验证知识注入已执行：确认非简单查询时 `retrieve_context.py` 已运行
6. 验证 knowledge_source 已记录：确认 plan JSON 含 `knowledge_source` 字段，降级时 `fallback_reason` 已填写
7. 验证指标扩展基于真实 code：确认 indicators 来自 context-card，非凭空猜测
8. 验证数据匹配为按需驱动：确认仅列出相关数据源，非全量扫描
9. 验证安全扫描已通过：确认所有输出经 `security_scan.py` 返回退出码 0
10. 验证错误处理遵循策略：确认重试/跳过/降级/中止决策匹配策略表
11. 验证无未脱敏 PII 残留：确认最终输出通过 P0/P1/P2 检测规则
