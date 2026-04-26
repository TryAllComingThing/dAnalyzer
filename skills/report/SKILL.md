---
name: report
description: 报告生成技能，支持日报、周报、月报、临时报告、对比报告、仪表盘等
---

# 报告生成技能 (Report)

## When to Activate

- Use this skill when generating reports or analytical documents
- Use this skill when creating daily reports, weekly reports, or monthly reports
- Use this skill when performing comparative analysis
- Use this skill when building dashboards or visualization configs
- Use this skill when creating ad-hoc analysis reports

## 核心能力

1. **日报生成** - 每日核心指标
2. **周报生成** - 每周汇总分析
3. **月报生成** - 深度月度分析
4. **临时报告** - 按需即时生成
5. **对比报告** - 环比/同比/竞品对比
6. **仪表盘** - 可视化仪表盘配置

## 子技能

| 子技能 | 文件 | 说明 |
|--------|------|------|
| 临时报告 | ad-hoc-report.md | 临时分析报告 |
| 对比报告 | comparison-report.md | 对比分析 |
| 日报 | daily-report.md | 每日报告 |
| 仪表盘 | dashboard-report.md | 仪表盘配置 |
| 月报 | monthly-report.md | 月度报告 |
| 周报 | weekly-report.md | 周报 |

## 使用场景

### 场景1: 周报生成
```
用户: 生成上周周报
→ 调用 report 技能 → 周报生成
→ 取数 → 指标计算 → 趋势分析
→ 输出周报文档
```

### 场景2: 对比分析
```
用户: 对比本月和上月数据
→ 调用 report 技能 → 对比报告
→ 环比分析
→ 输出对比结果
```

## 依赖配置

- skills/data-query - 数据查询
- skills/data-clean - 数据清洗
- skills/data-analysis - 数据分析
- skills/visualization - 可视化
- rules/core/indicator-caliber.md - 指标口径
