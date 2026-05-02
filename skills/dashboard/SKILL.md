---
name: dashboard
description: 静态 ECharts HTML 看板生成，多图表集成、自适应布局
---

# 数据分析看板技能 (Dashboard)

## When to Activate

- Use this skill when user wants a complete HTML dashboard page with multiple charts
- Use this skill when generating data report dashboard for business review
- Use this skill when creating executive dashboards with multiple KPIs

## HTML 生成规范（强制执行）

**生成看板 HTML 前必须加载 visual 的页面外壳，禁止从零编写完整 HTML。**

```
1. Read skills/visual/assets/page-chrome.html → 获取页面外壳（含下载工具栏、响应式 CSS、ECharts 初始化）
2. 替换占位符：{{ PAGE_TITLE }}、{{ DATE_RANGE }}、{{ GENERATED_AT }}、{{ SECURITY_NOTE }}
3. 在 {{ CONTENT }} 按下列结构注入：
   - KPI 摘要卡片区（使用 .kpi-grid > .kpi-card 结构）
   - 多图表网格区（每个图表使用 .chart-card 结构，含图表级下载按钮）
   - 明细数据表区（使用 .data-table 结构）
4. 将全部图表数据注入 {{ ALL_DATA_JSON }}
5. 每个图表调用 registerChart(domId, option) 注册实例
6. 下载按钮位置、样式、行为由 page-chrome.html 统一定义，不得自行修改
```

## 核心能力

1. **完整HTML看板生成** ⭐ — 一键生成完整HTML页面，多ECharts图表集成
2. **ECharts集成** — 多个ECharts图表在同一页面展示
3. **自适应多端** ⭐ — PC/平板/手机自适应布局
4. **看板设计** — 布局规划、组件配置、主题定制

## 依赖配置

- skills/data-query - 数据查询
- skills/data-analysis - 数据分析
- skills/visual - 可视化（ECharts）+ 页面外壳（page-chrome.html）
- skills/security - 安全脱敏（输出前处理，下载数据时）
- skills/visual/references/chart-standard.md — 图表规范
- skills/visual/assets/page-chrome.html — HTML 页面外壳（含下载工具栏）
- ECharts CDN: https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js
