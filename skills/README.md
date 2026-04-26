# 技能目录 (skills)

## 目录用途

数分全链路技能包，是 Agent 可调用的具体能力单元。每个技能目录包含主技能入口 (SKILL.md) 和若干子技能文件。

> 设计理念：按需加载，完整指令仅在需要时读取

## 目录结构

```
skills/
├── data-analysis/        # 数据分析技能
│   └── SKILL.md
├── data-clean/           # 数据清洗
│   ├── SKILL.md
│   └── ...
├── data-quality-check/  # 数据质量检查
│   └── SKILL.md
├── data-query/          # 数据查询
│   ├── SKILL.md
│   └── references/
├── dashboard/           # 看板技能
│   ├── SKILL.md
│   ├── layout-config.md
│   ├── component-lib.md
│   ├── real-time-data.md
│   ├── alert-rules.md
│   ├── permission-control.md
│   ├── theme-custom.md
│   ├── mobile-adaptive.md
│   └── export-share.md
├── danalyzer-guide/     # 入门指南
│   └── SKILL.md
├── insight-gen/        # 洞察生成
│   └── SKILL.md
├── model/              # 数据建模 (包含RFM、漏斗、归因等)
│   ├── SKILL.md
│   ├── rfm-model.md
│   ├── funnel-model.md
│   ├── attribution-model.md
│   └── ...
├── query/              # 高级查询 (7文件)
│   └── ...
├── report/             # 报告模板 (7文件)
│   └── ...
├── security/           # 安全合规 (包含脱敏、合规)
│   ├── SKILL.md
│   ├── audit-log-gen.md
│   ├── compliance-check.md
│   ├── masking-engine.md
│   └── ...
└── visual/             # 可视化 (8文件)
    └── ...
```

## 技能列表 (15个)

| 技能 | 说明 | 子技能数 | 触发条件 |
|------|------|----------|----------|
| data-query | 多数据源查询 | - | 用户需要从数据库/文件取数 |
| data-clean | 数据清洗 | 6 | 数据有空值/异常值/重复 |
| data-analysis | 数据分析 | - | 需要统计分析 |
| data-quality-check | 数据质量检查 | - | 需要校验数据质量 |
| security | 安全合规 | 7+ | 需要数据脱敏/合规检查 |
| model | 数据建模 | 8+ | 需要RFM/漏斗/归因/预测等高级分析 |
| query | 高级查询 | 6 | 需要复杂查询 |
| report | 报告生成 | 6 | 需要生成报告 |
| visual | 可视化 | 7 | 需要生成图表 |
| dashboard | 看板技能 | 9 | 需要数据看板/仪表盘 |
| insight-gen | 洞察生成 | - | 需要自动生成分析洞察 |
| danalyzer-guide | 入门指南 | - | 新用户入门引导 |

## 核心 Skills 说明

### data-query (数据查询)
- **职责**：多数据源统一查询
- **支持**：Hive、ClickHouse、MySQL、Excel、CSV

### data-clean (数据清洗)
- **职责**：数据质量清洗
- **能力**：空值处理、异常值处理、重复值处理、格式标准化

### data-quality-check (数据质量检查)
- **职责**：数据质量校验（REVIEWER模式）
- **能力**：空值检测、异常值检测、重复检测、连续性检测

### query (高级查询)
- **职责**：复杂查询
- **能力**：聚合查询、跨库关联、队列查询、漏斗查询

### model (数据建模)
- **职责**：高级数据建模（统一入口）
- **子技能**：RFM模型、漏斗模型、归因模型、聚类模型、预测模型等
- **说明**：整合了原来独立的 rfm-analysis、funnel-analysis

### security (安全合规)
- **职责**：安全脱敏 + 合规检查（统一入口）
- **子技能**：敏感数据检测、脱敏处理、PII识别、合规检查、审计日志
- **说明**：整合了原来独立的 compliance

### visual (可视化)
- **职责**：图表生成
- **能力**：折线图、柱状图、饼图、散点图、热力图等

### report (报告生成)
- **职责**：报告输出
- **能力**：日报、周报、月报、临时报告、仪表盘报告

### dashboard (看板技能)
- **职责**：数据看板/仪表盘构建
- **能力**：布局配置、组件库、实时数据、告警规则、权限控制

### insight-gen (洞察生成)
- **职责**：自动生成数据洞察和分析结论
- **能力**：趋势洞察、异常洞察、对比洞察、构成洞察、周期洞察

## 技能依赖关系

```
data-query (取数)
    ↓
query (复杂查询)
    ↓
data-clean (清洗) → data-quality-check (校验)
    ↓
data-analysis (分析)
    ↓
model (高级建模: RFM/漏斗/归因/预测)
    ↓
security (脱敏) → 合规检查
    ↓
visual (可视化) → report (报告) → dashboard (看板)
    ↓
insight-gen (洞察生成)
```

## 文件统计

- 主技能: 15个
- 子技能文件: 50+个
- **总计: 65+个 md 文件**

## 与 Agents 的关系

| 层级 | 说明 |
|------|------|
| Agent (danalyzer-core) | 执行主体，负责决策和流程控制 |
| Skill | 能力单元，提供具体操作能力 |
| Agent 调用 Skill | danalyzer-core 根据需求调用对应 Skill |

## 注意事项

1. 技能执行必须输出标准化结果
2. 脱敏类技能必须先调用 security
3. 技能间通过标准化接口传递数据
4. 使用标准英文格式的 "When to Activate" 触发条件
5. RFM分析 → 使用 model 技能（包含 rfm-model）
6. 漏斗分析 → 使用 model 技能（包含 funnel-model）
7. 合规检查 → 使用 security 技能
