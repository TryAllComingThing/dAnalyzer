---
name: dashboard
description: Use when user wants a complete multi-chart HTML dashboard page with KPI cards, chart grids, and data tables in a single responsive layout. Do NOT use for single standalone charts, Markdown text reports, or real-time monitoring dashboards.
---

# 数据分析看板技能 (Dashboard)

## 概述

静态 ECharts HTML 看板生成技能。将多个图表（KPI 卡片 + 趋势图 + 对比图 + 占比图 + 明细表）集成到单个自适应 HTML 页面中。复用 visual 的 page-chrome.html 外壳，提供统一的下载工具栏和响应式布局。

## 何时使用

- **触发:** 用户需要完整的多图表 HTML 看板页面
- **触发:** 用户需要含 KPI 卡片和图表网格的业务概览页面
- **触发:** 用户需要整合多数据视图的管理看板
- **不要用于:** 单个独立图表（使用 visual）
- **不要用于:** Markdown 文字报告（使用 report）
- **不要用于:** 实时监控（本技能生成静态 HTML 快照）

---

## 核心步骤

1. **加载外壳** — `Read skills/visual/assets/page-chrome.html` → 详见「HTML 生成规范」
2. **获取分析数据** — 通过 Connector 读取 data-analysis/model 的分析结果
3. **设计布局** — 确定 KPI 卡片数、图表网格（1-4 列自适应）、是否需要明细表 → 详见「HTML 生成规范」
4. **注入内容** — KPI 卡片 → 图表卡片（每个含 `.chart-insight`）→ 明细数据表 → 详见「HTML 生成规范」
5. **注入数据** — 全部图表原始数据写入 `{{ ALL_DATA_JSON }}` → 详见「HTML 生成规范」
6. **注册图表** — 每个图表调用 `registerChart(domId, option)` → 详见「HTML 生成规范」
7. **安全脱敏** — 输出前经 security 扫描

---

## HTML 生成规范（强制执行）

> 对应 核心步骤 第 1, 3-6 步

**生成看板 HTML 前必须加载 visual 的页面外壳，禁止从零编写完整 HTML。**

```
1. Read skills/visual/assets/page-chrome.html → 获取页面外壳（含下载工具栏、响应式 CSS、ECharts 初始化）
2. 替换占位符：{{ PAGE_TITLE }}、{{ DATE_RANGE }}、{{ GENERATED_AT }}、{{ SECURITY_NOTE }}
3. 在 {{ CONTENT }} 按下列结构注入：
   - KPI 摘要卡片区（使用 .kpi-grid > .kpi-card 结构）
   - 多图表网格区（每个图表使用 .chart-card 结构，含图表级下载按钮）
   - 每个图表容器下方必须有 `.chart-insight` 数据解释区块（格式见 visual SKILL.md「数据解释规范」）
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

---

## 常见借口与纠正

| 借口 | 现实 |
|--------|---------|
| "看板和单图表一样，多放几个 div 就行" | 看板需要布局规划（KPI 摘要 → 图表网格 → 明细表），直接堆砌会导致信息层级混乱 |
| "每个图表不用都写数据解读" | 看板中每个图表独立存在，无解读用户无法理解各图表间的逻辑关系 |
| "页面外壳的样式可以自己改" | 下载按钮位置/样式/行为由外壳统一定义；自行修改破坏一致性 |

## 红线

- **外壳未加载:** 未加载 page-chrome.html 从零编写 HTML — 违反架构约定，丢失下载工具栏
- **图表过多:** 单页超过 10 个图表 — 导致性能下降，需分页或降采样
- **数据不一致:** KPI 卡片数值与对应图表数据不匹配 — 输出前交叉验证
- **下载数据未脱敏:** 图表数据在下载中暴露未脱敏 — PII 可能泄露
- **洞察缺失或过短:** 任一 `.chart-insight` 区块缺失或短于 2 句 — 用户失去业务上下文

## 验证

1. 验证外壳加载：确认 page-chrome.html 已被 Read 且用作基础模板
2. 验证布局完整：确认 KPI 卡片、图表网格、明细表区域均已就位
3. 验证图表洞察：确认每个图表有独立的 `.chart-insight` 区块且 ≥2 句
4. 验证图表注册：确认每个图表在渲染后调用了 `registerChart(domId, option)`
5. 验证数据 JSON：确认 `{{ ALL_DATA_JSON }}` 包含所有图表的源数据
6. 验证响应式布局：确认页面在 PC、平板、手机断点下渲染正确
