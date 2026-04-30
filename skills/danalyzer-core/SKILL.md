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
- 异常时 spawn error-handler Agent

**技能编排参考表、分析类型决策、图表选型见 `analysis-reference.md`（按需读取）。**

---

## 一、检测规则

**触发条件**（满足任一即激活本 Skill）：

| 信号 | 示例 |
|------|------|
| 数据查询意图 | "查询"、"取数"、"SQL"、"导出"、"统计"、"计算" |
| 分析意图 | "分析"、"趋势"、"对比"、"归因"、"漏斗"、"留存" |
| 建模意图 | "RFM"、"聚类"、"分群"、"预测"、"评分" |
| 报表意图 | "日报"、"周报"、"月报"、"看板"、"dashboard" |
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
| 子技能必须加载 | Skill 包含子技能文件时（如 rfm-model.md），必须读取对应文件 |
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

## 七、上下文检索

按需检索行业知识。需要时调用 context-retriever skill：

- 用户输入包含行业特征词（如"配送时效"、"销售额"、"产能利用率"）
- 需要生成 SQL 查询
- 尚未加载行业上下文

---

## 八、调用协议（资产路径与加载方式）

### 技能加载

技能是通过 Read 文件加载的。按需 Read 以下路径获取具体指令：

| 技能 | 主文件 | 子技能 |
|------|--------|--------|
| context-retriever | `skills/context-retriever/SKILL.md` | - |
| data-query | `skills/data-query/SKILL.md` | - |
| data-clean | `skills/data-clean/SKILL.md` | `skills/data-clean/null-abnormal-clean.md`, `deduplication.md`, `format-standardize.md`, `outlier-handling.md`, `text-cleaning.md` |
| data-quality-check | `skills/data-quality-check/SKILL.md` | - |
| data-analysis | `skills/data-analysis/SKILL.md` | - |
| model | `skills/model/SKILL.md` | `skills/model/rfm-model.md`, `funnel-model.md`, `forecasting-model.md`, `cohort-analysis.md`, `clustering-model.md`, `attribution-model.md`, `correlation-analysis.md`, `trend-analysis.md` |
| visual | `skills/visual/SKILL.md` | `skills/visual/chart-standard.md` |
| report | `skills/report/SKILL.md` | `skills/report/daily-report.md`, `weekly-report.md`, `monthly-report.md`, `comparison-report.md`, `ad-hoc-report.md`, `dashboard-report.md` |
| dashboard | `skills/dashboard/SKILL.md` | - |
| security | `skills/security/SKILL.md` | `skills/security/sensitive-detection.md`, `sensitive-desensitize.md`, `pii-detection.md`, `masking-engine.md`, `masking-rules.md`, `compliance-check.md`, `audit-log-gen.md` |
| insight-gen | `skills/insight-gen/SKILL.md` | - |
| danalyzer-guide | `skills/danalyzer-guide/SKILL.md` | - |

**加载规则**：单个技能链中，每个技能的主文件 Read 1 次，子技能按需 Read。

### 脚本调用

| 用途 | 命令 |
|------|------|
| 行业上下文检索 | `python scripts/retrieve_context.py --query "<关键词>" --industry <行业>` |
| 数据查询执行 | `python scripts/execute_query.py --sql "<SQL>"` |
| 安全脱敏扫描 | `python scripts/security_scan.py --stdin`（管道输入）或 `--file <path>` |
| 指标报告生成 | `python scripts/generate_metrics_report.py --industry <行业>` |

所有脚本在 `scripts/` 目录下，项目根目录执行。

### 规则检查点

规则文件在 `rules/` 目录，4 级：legal > core > base > dynamic。

| 检查点 | 规则文件 | 强制？ |
|--------|----------|--------|
| SQL 生成前 | `rules/base/sql-write.md` | 建议 |
| 指标计算前 | `rules/core/indicator-caliber.md` | 是（不一致则阻止） |
| 时间维度使用前 | `rules/core/dimension-standard.md` | 是（格式不匹配则阻止） |
| 文件命名时 | `rules/base/file-naming.md` | 建议 |
| 报告输出前 | `rules/base/report-format.md` | 建议 |
| 数据导出前 | `rules/legal/export-control.md` | 是（超量/敏感字段则拦截） |
| 最终输出前 | `rules/legal/privacy-protection.md`, `rules/legal/data-security.md`, `rules/legal/sensitive-data.md` | 是（PII未脱敏则终止） |
| 动态规则有效期 | `rules/dynamic/*.md` | 按有效期 |

### 行业数据检索

数据在 `data/industry/<行业>/` 目录：

```
data/industry/
├── _base/          # 通用基础（6 指标 + 3 场景 + 字段映射）
├── ecommerce/      # 电商（3 指标 + 2 场景 + 5 表映射）
├── finance/        # 金融（3 指标 + 2 场景 + 4 表映射）
├── logistics/      # 物流（3 指标 + 1 场景 + 4 表映射）
└── manufacturing/  # 制造（3 指标 + 2 场景 + 4 表映射）
```

每个行业的 `.db` 文件由 IndustryStore 自动同步生成，通过 `python scripts/retrieve_context.py` 统一检索。

### 完整执行链路

```
用户请求
  │
  ├─ [Step 1] Read danalyzer-core/SKILL.md（编排框架）
  ├─ [Step 2] 需求拆解（Section 二）
  ├─ [Step 3] 复杂度判定 + 技能编排（Section 三 + analysis-reference.md）
  ├─ [Step 4] 行业上下文注入 → python scripts/retrieve_context.py（按需）
  ├─ [Step 5] 逐技能执行：
  │   ├─ Read skills/<skill>/SKILL.md → 获取具体指令
  │   ├─ Read 子技能文件（如有）
  │   ├─ 执行技能操作（查询/清洗/分析/建模/可视化）
  │   └─ 必要时查规则文件
  ├─ [Step 6] 安全门禁 → python scripts/security_scan.py（强制）
  └─ [Step 7] 返回结果
```
