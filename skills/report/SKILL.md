---
name: report
description: 报告生成 — 日报、周报、月报、对比报告、临时报告。输出前必须经 security 脱敏。
---

# Report — 报告生成技能

## 定位

report 负责将分析结果组织为结构化报告。所有报告输出前必须经过 `security` 脱敏。

**生成流程：**
```
1. 确定报告类型 → 从报告类型表找到对应模板段落
2. Read skills/report/assets/report-template.md → 按「数据来源映射」表将上游数据列映射到占位符
3. 填充模板 → 数值占位符填数据、自由文本占位符填 Claude 撰写的叙述
4. 图表占位符填 Markdown 图片语法: ![标题](output/chart_xxx.png)
5. 调用 CSVConnector 写入同名 .csv 数据附件
6. 经 security 脱敏后输出 .md + .csv
```

---

## 报告类型

| 类型 | 结构概要 | 模板 |
|------|----------|------|
| **日报** | 今日概览 → 实时数据 → 核心指标趋势 → 异常预警 → 关注事项 | `assets/report-template.md` |
| **周报** | 本周摘要 → 核心指标（环比）→ 维度拆解 → TOP 榜单 → 异常说明 → 下周关注 | `assets/report-template.md` |
| **月报** | 月度摘要 → 指标趋势（同比+环比）→ 渠道/商品/用户深度分析 → 异常检测 → 下月展望 | `assets/report-template.md` |
| **对比报告** | 对比概览 → 差异明细 → 可视化对比 → 原因分析 → 结论建议 | `assets/report-template.md` |
| **临时报告** | 自由结构，按用户需求定制 | 无固定模板，参见 `references/comparison-report.md` 的三种对比类型 |

## 核心指标模板

### 电商通用指标

| 指标 | 计算公式 |
|------|---------|
| GMV | `SUM(actual_amount)` |
| 订单量 | `COUNT(DISTINCT order_id)` |
| 客单价 | `GMV / 订单量` |
| 转化率 | `下单用户数 / 访问用户数` |
| 退款率 | `退款订单数 / 总订单数` |
| ARPU | `GMV / 用户数` |

### 环比/同比

`环比 = (本期-上期)/上期 × 100%`  `同比 = (本期-去年同期)/去年同期 × 100%`

### 变化判定

| 阈值 | 标记 | 行动 |
|------|------|------|
| ≤5% | 持平 | 正常波动 |
| 5-10% | 小幅 ↑/↓ | 关注 |
| 10-20% | 显著 ↑/↓ | 分析原因 |
| >20% | 大幅 ↑/↓ | 必须解释 |
| >50% | 异常 ↑/↓ | 核验数据 |

## 报告格式规范

- 标题包含时间范围和主题，摘要 3-5 句先结论后数据
- 数字千分位分隔，保留 1-2 位小数
- 每个图表有标题和轴标签（含单位），配色统一使用 skills/visual/references/chart-standard.md

### 报告导出

```
输出格式: Markdown
数据附件: CSV（与报告正文同名，同目录）
命名规范: {报告类型}_{日期}.md / .csv
```

## 依赖

- **上游**: skills/data-query, skills/data-analysis
- **可视化**: skills/visual
- **安全（强制）**: skills/security
