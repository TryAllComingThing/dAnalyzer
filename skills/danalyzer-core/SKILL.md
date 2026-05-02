---
name: danalyzer-core
description: dAnalyzer 核心调度器 — 数据分析请求的唯一编排入口。需求拆解、复杂度判定、错误处理、执行纪律。
---

# dAnalyzer Core — 编排调度器

## 核心职责

- 检测并路由数据分析请求
- 理解并拆解用户需求（模糊需求 → AskUserQuestion）
- 按复杂度决策执行策略（简单直接执行 / 复杂先出计划）
- 按需编排技能链（选择哪些 Skills、什么顺序）
- 协调执行并返回结果
- 技能异常时按策略表自行处理（见 Section V）

**技能编排参考表、分析类型决策、图表选型见 `analysis.md`（按需读取）。**

---

## 一、检测规则

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

## 二、需求拆解

### 模糊判断标准

满足任一即判定为"需求模糊"，必须 AskUserQuestion 澄清：

| 判断条件 | 示例 |
|---------|------|
| 缺少时间范围 | "分析销售情况"（未说明近7天/本月/全年） |
| 缺少指标定义 | "看下用户数据"（未说明看什么指标） |
| 缺少输出形式 | "分析下数据"（未说明要图表/报告/表格） |
| 多重解释可能 | "分析产品"（指产品销量、评价还是库存？） |

### AskUserQuestion 格式

每项 2~4 个选项，优先单选：

- **时间范围**：["本月", "上月", "近3个月", "近1年", "自定义"]
- **业务维度**：["按区域", "按产品线", "按客户类型", "不拆分"]
- **输出形式**：["图表看板", "报告", "数据表格", "自定义（请说明）"]

禁止仅输出文字选项而不调用 AskUserQuestion 工具，禁止猜测后直接执行。

### 分析指引场景（意图明确，执行阶段澄清）

以下场景意图已明确为 DATA_DEEP，**不在 Step 2 触发 AskUserQuestion**，
由 Agent 在执行阶段按对应方式主动澄清后继续：

| 场景 | 判定信号 | 处理方式 |
|------|----------|----------|
| 预测无历史 | 要求预测/预估，但未提供历史数据范围 | 先反问确认回溯窗口和时间粒度，确认后继续 |
| 指标未定义 | 指标有多个业务口径（如"活跃度"） | 列出可选口径（DAU/MAU/WAU 等），让用户选择 |
| 大范围分析 | 时间跨度极大或数据量巨大（全量/多年） | 建议缩小范围或抽样策略，用户确认后执行 |
| 伪分析 | 无数据或仅片段数据但要求深度分析 | 说明数据局限性，按有限数据做分析或引导补充数据 |

这些场景的 AskUserQuestion 在技能链执行时触发，而非需求拆解阶段。

### 2.5 结构化分析计划（Phase 2 — 动态注册表 + 语义转写）

需求明确后，**先获取知识库当前可用资源**，再输出结构化 JSON 分析计划。

#### Step 2.5a: 获取动态注册表

```bash
python scripts/registry_scanner.py --format context-card
```

输出当前 `knowledge/industry/` 下所有行业的**实时指标 code、场景 code、模型列表**。
新增的行业/指标/场景无需更新配置文件，自动出现在此输出中。

#### Step 2.5b: 输出分析计划 JSON

根据 context-card 中的真实 code 列表填写。**严格 JSON，无额外文字**：

```json
{
  "industry": "fmcg",
  "intent_id": "sales_diagnostic",
  "analysis_type": "diagnostic",
  "confidence": 0.9,
  "indicators": ["sales_amount", "order_count"],
  "scenarios": ["sales_trend"],
  "models": ["attribution-model"],
  "dimensions": ["category", "time"],
  "skill_chain": ["data-query", "data-clean", "data-analysis", "model", "visual", "report", "security"],
  "reasoning": "用户问品类表现不好的原因，属于诊断性分析，需归因模型"
}
```

**字段填值规则**：

| 字段 | 规则 |
|------|------|
| `industry` | 从 context-card 中匹配 trigger_keywords 与用户输入最相关的行业 |
| `intent_id` | 从 `knowledge/intent-routing.yaml` 的 `intents` 中匹配 `keywords` 最相关的一项 |
| `analysis_type` | 从匹配到的 intent 取，或自行判断：descriptive / diagnostic / predictive / prescriptive / exploratory |
| `confidence` | 自评 0.0-1.0 |
| `indicators` | **必须使用 context-card 中存在的 indicator_code**，至少 2 个 |
| `scenarios` | **必须使用 context-card 中存在的 scenario_code**，至少 1 个 |
| `models` | 参考 intent 的 `models` |
| `skill_chain` | 参考 context-card 底部的 `analysis_type → skill_chain` 映射 |

#### Step 2.5c: 执行检索

```bash
python scripts/retrieve_context.py \
  --query "<原始查询>" \
  --plan '<上述JSON>'
```

**`--industry` 可选**（不传则自动从 plan 中提取，或按 trigger_keywords 检测）。

#### 兜底保证

该命令内部走 L1 精确查询 → L2 FTS 模糊搜索 → L3 LLM 推理的三级兜底。
即使 Step 2.5b 的 JSON 中有个别 code 拼错，校验层自动过滤 + 场景反查补齐。JSON 完全写错时 L2 接住。

> **Phase 2 核心改进：** `registry_scanner.py` 动态扫描文件系统，新增行业/指标/场景**零配置**自动可用。LLM 始终拿到最新的 code 列表，从源头消除幻觉。

---

## 三、复杂度判定

| 请求示例 | 判定 | 处理方式 |
|----------|------|----------|
| "查询订单数量" | 简单 | 直接 data-query → security |
| "上月GMV" | 简单 | 直接 data-query → security |
| "各渠道用户数" | 简单 | 直接 data-query → security |
| "查询销售趋势并画图" | 中等 | data-query → visual → security |
| "导出为CSV" | 简单 | data-query → export → security |
| "分析上个月销售趋势" | 复杂 | 需求拆解 → 多技能编排 |
| "RFM用户分层" | 复杂 | 需求拆解 → 多技能编排 |
| "生成Q1月报" | 复杂 | 需求拆解 → 任务规划 → 多技能编排 |
| "销售看板" | 复杂 | 需求拆解 → 多技能编排 |
| "漏斗分析" | 复杂 | 需求拆解 → 多技能编排 |

### 决策规则表

| 需求明确？ | 任务复杂？ | 动作 |
|-----------|-----------|------|
| 明确 | 简单（≤2 技能） | 跳过拆解，直接执行 |
| 明确 | 复杂（>2 技能或有依赖） | 给出执行计划后再执行 |
| 模糊 | 简单 | 先澄清需求，再执行 |
| 模糊 | 复杂 | 先澄清需求，再给出执行计划 |

---

## 四、执行纪律规则

| 规则 | 说明 |
|------|------|
| Skill 规则优先 | SKILL.md 中定义的标准/公式/评分规则优先级高于通用知识 |
| 子技能必须加载 | Skill 包含子技能文件时（如 references/rfm-analysis.md），必须读取对应文件 |
| 禁止跳过 Skill | 存在对应 Skill 时禁止用自身知识替代执行 |
| 数据 I/O 用 Connector | 禁止手写 csv/json 读写，统一使用 connectors/ 接口 |

---

## 五、错误处理

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

---

## 六、安全规范

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

## 七、上下文检索（强制执行）

**非简单查询时，Step 2.5 为硬触发条件，不可跳过。**

| 查询复杂度 | 触发规则 |
|-----------|----------|
| 简单查询（"查询订单数量"、"上月GMV"） | 可跳过，指标明确无需检索 |
| 中等/复杂（含分析/建模/报表/可视化意图） | **强制执行 Step 2.5**，不可跳过 |
| 含行业特征词（"配送时效"、"销售额"、"产能利用率"等） | **强制执行 Step 2.5**，即使查询简单 |

判断标准：若 Section III 复杂度判定为中等或复杂，则 Step 2.5 为强制步骤。

**Phase 1 流程**（取代旧的直接 Read 文件方式）：

```
Step 2.5 输出结构化 plan JSON
  → python scripts/retrieve_context.py --plan '<json>' --query "<原文>"
    → L1: 精确 code 查询（校验层过滤幻觉 code）
    → L2: FTS5 + 向量 + RRF 模糊检索（L1 失败/不足时自动降级）
    → L3: 返回 routing_context 供 Agent 推理（L1/L2 均空时）
```

**行业自动检测**：不传 `--industry` 时，脚本自动从 `intent-routing.yaml` 的 `trigger_keywords` 匹配行业。

**手动检索**（调试/极端情况）：`python scripts/retrieve_context.py --query "关键词" --industry fmcg`（无 plan 时直接走 L2）。

---

## 八、调用协议（资产路径与加载方式）

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

### 脚本调用

| 用途 | 命令 |
|------|------|
| 行业上下文检索 | `python scripts/retrieve_context.py --query "<关键词>" --industry <行业>` |
| 数据查询执行 | `python scripts/execute_query.py --sql "<SQL>"` |
| 安全脱敏扫描 | `python scripts/security_scan.py --stdin`（管道输入）或 `--file <path>` |
| 指标报告生成 | `python scripts/generate_metrics_report.py --industry <行业>` |

所有脚本在 `scripts/` 目录下，项目根目录执行。

### 行业数据检索

数据在 `knowledge/industry/<行业>/` 目录：

```
knowledge/industry/
└── fmcg/           # 快消（8 指标 + 4 场景 + 字段映射）
```

每个行业的 `.db` 文件由 IndustryStore 自动同步生成，通过 `python scripts/retrieve_context.py` 统一检索。

### 完整执行链路

```
danalyzer Agent 内建执行协议，启动后立即执行:
  │
  ├─ [Step 1] 需求拆解 + AskUserQuestion（模糊时）
  ├─ [Step 2] 复杂度判定 + 决策分支（简单直接/复杂先计划）
  ├─ [Step 3] 行业上下文注入 → python scripts/retrieve_context.py（非简单时强制）
  ├─ [Step 4] 逐技能执行：
  │   ├─ 按技能加载表 Read skills/<skill>/SKILL.md → 获取具体指令
  │   ├─ Read 子技能文件（如有）
  │   └─ 必要时查 rules/ 规则文件
  ├─ [Step 5] 安全门禁 → python scripts/security_scan.py（强制）
  └─ [Step 6] 返回结果
```

> 本文件为完整编排参考。Agent 内建了执行协议核心表，无需启动时 Read 本文件。执行详细规则（指标口径/时间维度/SQL规范等）按需查阅 rules/。
