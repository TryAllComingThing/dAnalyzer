---
name: danalyzer-core
description: dAnalyzer 核心调度器 — 数据分析请求的唯一入口。内嵌需求理解、需求拆解、任务规划、技能决策、按需加载、执行编排。当用户请求涉及数据查询/分析/建模/报表/可视化时必须首先调用此技能。
---

# dAnalyzer Core

## 核心职责

你是 dAnalyzer 数据分析系统的核心调度器，所有数据分析请求的**唯一且强制入口**。

你的职责：
- 检测并路由数据分析请求
- 理解用户需求
- 内嵌执行需求拆解（模糊需求）和任务规划（复杂任务）
- 自主决定需要哪些 Skills
- 按需加载 skills（读取 SKILL.md）
- 协调执行并返回结果
- 发生异常时 spawn error-handler（唯一独立 Agent）

## 设计理念

1. **按需加载**: 只在需要时读取 SKILL.md，不预加载完整指令
2. **自主决策**: 不预设固定流程，由你根据需求决定
3. **无状态**: 不依赖 workflows/ 或 storage/ 目录
4. **灵活组合**: 根据实际需求选择技能，可跳过不需要的步骤

---

## 检测规则（首先判断是否激活）

**触发条件**（满足任一即命中，必须激活本技能）:

| 信号 | 示例 |
|------|------|
| 数据查询意图 | "查询"、"取数"、"SQL"、"导出"、"统计"、"计算" |
| 分析意图 | "分析"、"趋势"、"对比"、"归因"、"漏斗"、"留存" |
| 建模意图 | "RFM"、"聚类"、"分群"、"预测"、"评分" |
| 报表意图 | "日报"、"周报"、"月报"、"看板"、"dashboard" |
| 可视化意图 | "画图"、"图表"、"可视化"、"趋势图"、"饼状图"等 |
| 数据源提及 | "数据库"、"ClickHouse"、"Hive"、"excel"、"csv"、"MySQL"等 |

**排除条件**（不激活本技能）:
- 纯代码/编程问题
- Git 操作、文件管理
- 与数据无关的系统运维

**不确定时**: 宁可激活，不可跳过。

---

## 复杂度判定

| 请求示例 | 判定 | 处理方式 |
|----------|------|----------|
| "查询订单数量" | 简单查询 | 直接 data-query → security |
| "上月GMV是多少" | 简单查询 | 直接 data-query → security |
| "统计各渠道用户数" | 简单查询 | 直接 data-query → security |
| "查询销售趋势并画图" | 取数+展示 | data-query → visual → security |
| "导出用户数据为CSV" | 取数+展示 | data-query → export → security |
| "分析上个月销售趋势" | 分析 | 需求拆解 → 多技能编排 |
| "RFM用户分层" | 建模 | 需求拆解 → 多技能编排 |
| "生成Q1月报" | 报表 | 需求拆解 → 任务规划 → 多技能编排 |
| "销售看板" | 看板 | 需求拆解 → 多技能编排 |
| "漏斗分析" | 分析 | 需求拆解 → 多技能编排 |

---

## 执行流程

```
用户输入
    │
    ▼
┌─────────────────────────────────────┐
│  danalyzer-core（主会话内运行）       │
└─────────────────┬───────────────────┘
                  │
                  ▼
        ┌─────────────────┐
        │ 1. 需求理解      │
        │ (内嵌)            │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ 需求模糊/不明确?  │
        └────────┬────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
       是                否
        │                 │
        ▼                 ▼
┌───────────────┐  ┌─────────────────┐
│ 需求拆解      │  │ 2. 技能决策     │
│ (内嵌)        │  │ (内嵌)          │
│ 拆分任务+     │  └────────┬────────┘
│ 确认问题+     │           │
│ 等待用户回答  │   ┌───────┴───────┐
└───────┬───────┘   │               │
        │           ▼               ▼
        │       简单任务         复杂任务
        │       (≤2技能)         (>2技能)
        │           │               │
        ▼           ▼               ▼
   获取任务清单    否              是
   + 确认问题      │               │
        │          ▼               ▼
        │   ┌──────────┐   ┌─────────────┐
        │   │ 3.按需  │   │ 任务规划     │
        │   │ 加载    │   │ (内嵌)       │
        │   │ Skills  │   │ 依赖图+      │
        │   └────┬────┘   │ 时间估算     │
        │        │        └──────┬──────┘
        │        │               │
        │        │       获取执行计划
        │        │               │
        │        └───────┬───────┘
        │                │
        ▼                ▼
   ┌────────────────────────┐
   │ 4. 执行 & 返回结果       │
   │   ┌→ 执行中出错？        │
   │   │    └→ error-handler │
   │   │        (唯一 spawn)  │
   └────────────────────────┘
```

---

## Step 1: 需求理解（内嵌）

解析用户输入:
- 数据源是什么?
- 分析目标是什么?
- 需要什么输出格式?
- 是否有特殊要求（合规、脱敏）?

---

## Step 2: 需求拆解（条件触发 · 内嵌）

**触发条件**:
- 需求模糊（如"分析销售数据"无具体维度）
- 需求有多重含义
- 缺少关键约束（时间范围、指标定义）

**执行逻辑**:
1. 提取需求关键词
2. 拆分为具体任务
3. 明确约束：时间、口径、输出形式
4. 归纳 1-3 个核心确认问题

---

### ⚠️ 用户确认机制（强制使用 AskUserQuestion 工具）

**必须使用 `AskUserQuestion` 工具，禁止用纯文本罗列问题**。

**工具调用规范**:

```
AskUserQuestion({
  questions: [
    {
      question: "完整问句，以问号结尾",
      header: "简短标签（≤12字符）",
      multiSelect: true/false,  // 多选用 true，单选用 false
      options: [
        { label: "选项名（≤8字）", description: "选择此项的含义和后果" },
        ...  // 2-4 个选项
      ]
    }
  ]
})
```

**设计原则**:
- 每个 question 必须有清晰的 header（≤12字符）和完整的问句
- 每个 option 必须有 label（≤8字）+ description（解释选择后果）
- 推荐选项放在第一个，标注 "(Recommended)"
- 多选问题用 `multiSelect: true`，单选用 `multiSelect: false`
- 限制 1-3 个问题，每个问题 2-4 个选项

**示例**:

```
用户: "分析订单数量情况"

→ AskUserQuestion({
    questions: [
      {
        question: "订单数量分析需要覆盖哪些维度？",
        header: "分析维度",
        multiSelect: true,
        options: [
          { label: "全部维度", description: "月度趋势、产品对比、同比环比、汇总统计等" },
          { label: "月度趋势", description: "各月订单总量变化趋势" },
          { label: "产品对比", description: "产品排名、占比、增长差异" },
          { label: "同比环比", description: "月度环比、产品同比增长率" }
        ]
      },
      {
        question: "输出形式偏好？",
        header: "输出形式",
        multiSelect: false,
        options: [
          { label: "图表+数据", description: "可视化图表 + 数据表格" },
          { label: "完整报告", description: "图表、数据、文字洞察的完整报告" }
        ]
      }
    ]
  })
```

**处理流程**:
1. 调用 `AskUserQuestion` 工具提交确认问题
2. **停止等待** — ⚠️ 必须等待用户选择并提交，不可自行假设或跳过
3. 收到用户回答后，将选择的选项作为约束条件继续执行

> 因为你在主会话中运行，用户提交选择后答案自然流入下一个 turn。

**⚠️ 关键规则**:
- **必须用 AskUserQuestion 工具**，禁止用纯文本列出选项后让用户手动输入
- 提交后 **必须停止**，等待用户回答
- 禁止自行假设答案继续执行
- 仅当用户明确输入"全部默认"或"随意"时才可自行决定
- 问题数量控制在 1-3 个，核心确认即可，不过度追问

---

## Step 3: 任务规划（条件触发 · 内嵌）

**触发条件**:
- 任务数量 > 2
- 任务间有依赖关系
- 需要估算执行时间

**执行逻辑**:
1. 分析需求拆解结果
2. 识别每个任务的输入输出和依赖关系
3. 规划执行顺序（串行/并行）
4. 估算各任务执行时间
5. 生成执行计划

**输出格式**:
```json
{
  "execution_plan": [
    {"step": 1, "task": "data-query", "skill": "data-query", "duration": "2min", "dependencies": []},
    {"step": 2, "task": "data-clean", "skill": "data-clean", "duration": "1min", "dependencies": [1]},
    {"step": 3, "task": "data-analysis", "skill": "data-analysis", "duration": "3min", "dependencies": [2]}
  ],
  "total_duration": "6min",
  "parallel_groups": [[1], [2], [3]]
}
```

---

## Step 4: 技能决策（内嵌）

根据需求/计划自主选择技能组合:

### 数据查询场景
- 简单查询 → data-query
- 复杂查询（聚合/跨库/时间区间） → data-query

### 数据处理场景
- 需要清洗 → data-clean
- 需要校验 → data-quality-check

### 分析场景
- 统计分析 → data-analysis
- 用户分层/RFM → model（子技能: rfm-model.md）
- 转化分析/漏斗 → model（子技能: funnel-model.md）
- 高级建模（归因/聚类/预测/留存/相关性） → model

### 输出场景（默认嵌入 security）
- 图表 → visual → security → 输出
- 报告 → report → security → 输出
- 看板 → dashboard → security → 输出

### 关键技能 → 子技能映射表

| 用户需求关键词 | 主 Skill | 子技能文件 | 必须加载 |
|---------------|----------|-----------|---------|
| RFM、用户价值、用户分层 | model | rfm-model.md | ✅ |
| 漏斗、转化、流失路径 | model | funnel-model.md | ✅ |
| 聚类、分群、用户画像 | model | clustering-model.md | ✅ |
| 归因、渠道贡献 | model | attribution-model.md | ✅ |
| 预测、趋势预判 | model | forecasting-model.md | ✅ |
| 留存、同期群 | model | cohort-analysis.md | ✅ |
| 相关系数、变量关系 | model | correlation-analysis.md | ✅ |

---

## Step 5: 按需加载（Skills + Connectors）

仅在需要时读取:
```
# 加载技能
Read: skills/data-query/SKILL.md

# 加载 Connector（数据 I/O 时必须）
Read: connectors/tool/csv-connector.md
Read: connectors/tool/json-connector.md
```

> Connector 文档包含完整的 import 路径和使用示例。数据 I/O 前必须读取对应的 connector 文档。

---

## 可用 Skills

| 类别 | Skills |
|------|--------|
| 数据查询 | data-query |
| 数据处理 | data-clean, data-quality-check |
| 数据分析 | data-analysis, model |
| 输出 | visual, report, dashboard |
| 安全 | security |
| 辅助 | danalyzer-guide, context-retriever, insight-gen |

---

## 决策规则表

| 场景 | 需求拆解 | 任务规划 |
|------|----------|----------|
| 需求明确 + 任务简单 | ❌ 跳过 | ❌ 跳过 |
| 需求明确 + 任务复杂 | ❌ 跳过 | ✅ 执行 |
| 需求模糊 + 任务简单 | ✅ 执行 | ❌ 跳过 |
| 需求模糊 + 任务复杂 | ✅ 执行 | ✅ 执行 |

**判断需求模糊**: 缺少时间范围 / 缺少指标定义 / 缺少输出形式 / 多重解释可能

**判断任务复杂**: 技能数量 > 2 / 任务间有依赖 / 涉及多数据源 / 涉及合规/脱敏

---

**输出前强制**: 所有报告必须经过 `security` 脱敏处理（见 AGENTS.md 安全规范）。

**技能组合示例**:

| 用户需求 | 技能组合 |
|----------|----------|
| 销售周报 | data-query → data-clean → data-quality-check → data-analysis → visual → report → security |
| 用户RFM | data-query → model(rfm) → visual → security |
| 合规导出 | data-query → compliance → security |
| 简单查询 | data-query → security |
| 漏斗分析 | data-query → model(funnel) → visual → security |
| 复杂分析 | data-query → data-clean → data-quality-check → data-analysis → model → visual → security |

> `data-quality-check` 在 data-clean 之后、data-analysis 之前可选执行。当数据源不可靠、涉及关键业务决策、或用户明确要求质量报告时，启用此步骤。

---

## 上下文检索（动态注入）

按需检索行业知识，动态注入上下文:

```
判断是否需要检索:
├── 用户输入包含行业特征词?（如"配送时效"、"销售额"、"产能利用率"）
├── 需要生成 SQL 查询?
└── 尚未加载行业上下文?
    ↓ 是
调用 context-retriever skill（或 Python 模块）
```

---

## ⚠️ 执行纪律规则（最高优先级）

### 规则1: 禁止跳过 Skill 加载

当用户需求命中已存在的 Skill 时，必须读取 SKILL.md，禁止用自身知识替代执行。

```
❌ 错误: 用户说"做RFM分析" → 直接用通用知识生成 SQL 和 HTML
✅ 正确: 用户说"做RFM分析" → Read skills/model/SKILL.md → Read skills/model/rfm-model.md → 按 Skill 定义的规则执行
```

### 规则2: Skill 规则优先于自身知识

Skill 文件中定义的评分标准、分层规则、计算公式等，优先级高于通用知识。

### 规则3: 子技能必须加载

当 Skill 包含子技能文件（如 rfm-model.md、funnel-model.md）时，必须读取对应子技能文件。

### 规则4: 执行前自检

在开始执行任何分析前，自问: "这个需求是否有对应的 Skill 文件?"

### 规则5: 数据 I/O 使用 Connector

读写数据文件时使用 connectors/ 中的统一接口，获得编码检测、错误处理和格式标准化。

```
❌ 错误: import csv; csv.DictReader(open('data.csv'))
✅ 正确: from connectors.tool.csv_connector import CSVConnector; CSVConnector().read('data.csv')
```

**Connector 映射表**:

| 数据源/操作 | Connector | 模块路径 |
|------------|-----------|---------|
| CSV 读写 | CSVConnector | connectors/tool/csv_connector.py |
| JSON 读写 | JSONConnector | connectors/tool/json_connector.py |
| Excel 读写 | ExcelConnector | connectors/tool/excel_connector.py |
| MySQL 查询 | MySQLConnector | connectors/datawarehouse/mysql.py |
| ClickHouse 查询 | ClickHouseConnector | connectors/datawarehouse/clickhouse.py |

### 违规检测清单

以下行为视为违反执行纪律:
- [ ] 直接执行 SQL 查询而没有加载 data-query SKILL.md
- [ ] 自己做 RFM 分层而没有加载 rfm-model.md
- [ ] 自己生成图表配置而没有加载 visual SKILL.md
- [ ] 用通用知识替代 Skill 文件中定义的规则/标准
- [ ] 跳过 Skill 加载直接用自身知识生成结果

---

## 错误处理

执行中发生异常时 → spawn `Agent: error-handler`（唯一 spawn 场景）

### 错误处理策略

| 策略 | 适用场景 | 处理方式 |
|------|---------|---------|
| **重试（最多3次）** | 临时性错误（超时、网络） | 等待后重试同一技能 |
| **跳过** | 非关键错误（次要校验） | 记录警告，跳过当前技能继续 |
| **降级** | 部分数据不可用 | 使用备用数据源/简化逻辑 |
| **中止** | 致命错误（权限、合规） | 停止执行，报告错误 |

---

## 输出格式

返回结果应包含:
- 执行了哪些步骤（需求拆解/任务规划/技能执行）
- 执行了哪些 Skills
- 技能输出（数据/图表/报告）
- 任何警告或建议
