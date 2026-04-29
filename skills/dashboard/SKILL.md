---
name: dashboard
description: 数据分析看板技能，支持完整HTML看板生成、ECharts多图表集成、自适应布局、实时监控、告警配置
---

# 数据分析看板技能 (Dashboard)

## When to Activate

- Use this skill when creating data dashboards or monitoring panels
- Use this skill when building real-time data monitoring
- Use this skill when configuring dashboard alerts and thresholds
- Use this skill when designing dashboard layouts and components
- Use this skill when setting up dashboard sharing and export
- Use this skill when user wants a complete HTML dashboard page with multiple charts
- Use this skill when generating data report dashboard for business review
- Use this skill when creating executive dashboards with multiple KPIs

## 核心能力

1. **完整HTML看板生成** ⭐ — 一键生成完整HTML页面，多图表集成
2. **ECharts集成** — 多个ECharts图表在同一页面展示
3. **自适应多端** ⭐ — PC/平板/手机自适应布局
4. **看板设计** — 布局规划、组件配置、主题定制
5. **实时数据** — WebSocket/轮询、实时刷新、自动更新
6. **交互式图表** — 悬停提示、缩放筛选、联动跳转
7. **告警配置** — 阈值告警、异常预警、通知推送
8. **权限管理** — 行级权限、列级权限、角色控制

## 依赖配置

- skills/data-query - 数据查询
- skills/data-analysis - 数据分析
- skills/visual - 可视化（ECharts）
- skills/report - 报告导出
- skills/security - 安全脱敏（输出前处理）
- rules/core/indicator-caliber.md - 指标口径
- data/template/dashboard-layout.md - 布局模板
- ECharts CDN: https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js
