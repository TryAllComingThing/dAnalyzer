# 月报生成技能

## 核心功能

按业务线、时间范围自动生成月报

## 输入参数

- 业务线
- 月份（如2026年4月）
- 数据文件路径

## 报告结构

1. 标题（业务线+月份）
2. 本月概览（核心指标）
3. 销售分析（趋势、渠道、商品）
4. 用户分析（规模、留存、价值）
5. 问题与机会
6. 下月计划

## 调用资源

- assets/template/report-template.md
- assets/indicator/core-indicator-dict.md
- assets/indicator/sales-indicator.md
- assets/indicator/user-indicator.md
- skills/query/multi-source-query.md
- skills/visual/chart-standard.md
- skills/clean/null-abnormal-clean.md

## 输出结果

- 月报文件（Markdown格式）
- 图表文件
- 执行日志
