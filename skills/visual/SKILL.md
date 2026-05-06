---
name: visual
description: Use when 用户要求画图、可视化、趋势图、对比图、占比图、热力图或 ECharts HTML 看板。Do NOT use for 纯数据表格、非 ECharts 图片生成或无数据支撑的示意图。
---

# 可视化技能 (Visual)

## 概述

ECharts 驱动的交互式图表生成技能。支持趋势图、对比图、分布图、占比图、热力图等常见图表类型，输出自适应 PC/平板/手机的 HTML 页面。强制使用 page-chrome.html 外壳模板，每个图表附带数据解读，支持 CSV/Excel 数据下载。

## 何时使用

- **触发:** 用户要求画图、可视化、趋势图、柱状图、饼图等图表
- **触发:** 用户需要 HTML 输出，要求 PC/平板/手机自适应展示
- **触发:** 用户要求查看或下载图表原始数据（CSV/Excel）
- **不要用于:** 纯数据表格无图表需求（走 report）
- **不要用于:** 非 ECharts 图片生成或无数据支撑的示意图

---

## 核心步骤

1. **获取数据** — 通过 Connector（JSONConnector/CSVConnector）读取上游分析结果
   → 详见「数据读写强制使用 Connector」

2. **选择图表类型** — 根据数据特征和用户意图匹配：趋势→折线图、对比→柱状图、占比→饼图/环形图、分布→直方图/箱线图、多维→热力图
   → 详见「核心能力」

3. **加载外壳** — `Read skills/visual/assets/page-chrome.html`，替换 `{{ PAGE_TITLE }}`、`{{ DATE_RANGE }}`、`{{ GENERATED_AT }}`、`{{ SECURITY_NOTE }}`
   → 详见「HTML 生成规范」

4. **生成图表** — 按图表类型构造 ECharts option。**饼图/环形图数据必须用 `{name, value}` 格式，禁止自定义键名**（如 `{gender, users}` 会导致图表空白）。注入 `{{ CONTENT }}`，每个图表容器下方附带 `.chart-insight` 数据解读（≥2 句）
   → 详见「HTML 生成规范」和「数据解释规范」

5. **注入数据与注册** — 所有图表原始数据写入 `{{ ALL_DATA_JSON }}`，每个图表调用 `registerChart(domId, option)`
   → 详见「HTML 生成规范」

6. **安全与边界检查** — 输出前经 security 扫描脱敏；超 1 万行数据需分页；敏感数据确认权限；Excel 注意分 Sheet
   → 详见「注意事项」

7. **交付输出** — 生成完整自适应 HTML 文件，验证下载工具栏（CSV/Excel）功能正常

---

## ⚠️ 数据读写强制使用 Connector

> 对应 核心步骤 第 1 步

**生成 HTML 前必须通过 Connector 读取分析结果，禁止用 `open()` / `json.load()` 裸读。**

| 操作 | Connector | 导入路径 |
|------|-----------|---------|
| 读 JSON | JSONConnector | `from connectors.tool.json_connector import JSONConnector` |
| 读 CSV | CSVConnector | `from connectors.tool.csv_connector import CSVConnector` |
| 写 CSV | CSVConnector | 同上 |
| 写 Excel | ExcelConnector | `from connectors.tool.excel_connector import ExcelConnector` |

读写示例见 `connectors/README.md`。

---

## HTML 生成规范（强制执行）

> 对应 核心步骤 第 3-5 步 — HTML 生成详细实现

**生成 HTML 前必须加载页面外壳，禁止从零编写完整 HTML。**

```
1. Read skills/visual/assets/page-chrome.html → 获取页面外壳（含下载工具栏、响应式 CSS、ECharts 初始化）
2. 替换占位符：{{ PAGE_TITLE }}、{{ DATE_RANGE }}、{{ GENERATED_AT }}、{{ SECURITY_NOTE }}
3. 在 {{ CONTENT }} 注入图表卡片（KPI 卡片 + 图表容器 + 数据解释 + 明细数据表）
4. 将各图表的原始数据注入 {{ ALL_DATA_JSON }}，供下载按钮使用
5. 每个图表调用 registerChart(domId, option) 注册实例
6. 每个图表容器下方必须有 `.chart-insight` 数据解释区块（见「数据解释规范」）
7. 下载按钮位置、样式、行为由 page-chrome.html 统一定义，不得自行修改
```

## 数据解释规范（强制执行）

> 对应 核心步骤 第 4 步 — 图表解读详细规范

**每个图表下方必须附带数据解释区块**，不可仅输出图表而无文字解读。

### 结构要求

```html
<div class="chart-card">
  <div class="chart-card-header">
    <span class="chart-card-title">图表标题</span>
  </div>
  <div class="chart-card-body">
    <div class="chart-container" id="chart-1"></div>
    <div class="chart-insight">
      <p><strong>洞察：</strong>[2-4 句话解释图表反映的核心趋势、关键数据点、业务含义]</p>
    </div>
  </div>
</div>
```

### 内容要求

| 要求 | 说明 |
|------|------|
| 核心趋势 | 数据整体走向（上升/下降/平稳/波动） |
| 关键数据点 | 最高值、最低值、拐点、异常值 |
| 业务含义 | 对业务决策的启示或建议 |
| 长度 | 2-4 句完整散句，不短于 2 句 |

### 示例

```
洞察：Q3 销售额环比增长 23%，其中 9 月达到峰值 1,280 万元。
增长主要由华东区贡献（占比 48%），华南区增速放缓明显。
建议重点关注华南区渠道覆盖，同时维持华东区增长势头。
```

### 多图表场景

- 每个图表独立附带自己的 `.chart-insight`，不可多个图表共用一个解释
- KPI 卡片仅显示指标名称和数值，不附加解释文字

---

## 核心能力

> 对应 核心步骤 第 2 步 — 图表类型选择参考

1. **ECharts集成** ⭐ — 完整ECharts配置，生成交互式HTML图表
2. **自适应多端** ⭐ — 输出HTML自动适配PC/平板/手机
3. **数据交互** ⭐ — 页面右上角统一下载工具栏（CSV/Excel），图表卡片内单图下载
4. **趋势图** — 折线图、面积图
5. **对比图** — 柱状图、条形图
6. **分布图** — 直方图、箱线图
7. **占比图** — 饼图、环形图
8. **热力图** — 颜色热力图
9. **仪表盘** — 可视化仪表盘

---

## 依赖配置

### Connector 模块

读写数据强制使用 Connector（详见「数据读写强制使用 Connector」节），禁止裸读写。

- skills/data-query - 数据查询
- skills/data-clean - 数据清洗
- skills/visual/references/chart-standard.md — 图表规范
- skills/visual/assets/export-template.md — 导出格式模板
- ECharts CDN: https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js

---

## 注意事项

> 对应 核心步骤 第 6 步 — 安全与边界约束

1. **数据安全**：下载数据需经过 security 技能脱敏处理
2. **大数据量**：超过1万行建议分页加载或提示用户
3. **权限控制**：敏感数据需检查权限后才能下载
4. **文件大小**：Excel导出有行数限制，建议分Sheet

---

## Common Rationalizations

| 借口 | 现实 |
|------|------|
| "就一个简单图表，直接从零写 HTML 更快" | 跳过 page-chrome.html 会丢失下载工具栏、响应式 CSS 和统一样式 |
| "图表已经很清楚了，不需要文字解读" | 无 `.chart-insight` 的图表用户无法理解业务含义 |
| "数据不多，不用 Connector 读，直接硬编码" | 绕过 Connector 导致数据来源不可追溯，且违反架构约定 |

## Red Flags

- **从零编写 HTML:** 未使用 page-chrome.html 外壳从零编写完整 HTML — 违反架构约定，丢失下载工具栏和响应式 CSS
- **缺少图表解读:** 任一图表容器缺少 `.chart-insight` 数据解读区块 — 用户无法理解业务含义
- **自行修改下载按钮:** 下载按钮位置、样式或行为被修改 — 必须使用外壳统一定义
- **页面拥挤:** 单页超过 10 个图表 — 考虑分页或降采样
- **饼图数据键名错误:** 饼图/环形图 data 未使用 `{name, value}` 格式 — 图表将空白，必须修正

## Verification

1. **验证外壳加载** — 确认 page-chrome.html 已被 Read 且用作模板，非从零编写
2. **验证占位符替换** — 确认 `{{ PAGE_TITLE }}`、`{{ DATE_RANGE }}`、`{{ GENERATED_AT }}`、`{{ SECURITY_NOTE }}` 均已替换为实际值
3. **验证图表解读存在** — 确认每个 `.chart-container` 下方有 `.chart-insight` 且 ≥2 句
4. **验证图表注册** — 确认每个图表在 DOM 插入后调用了 `registerChart(domId, option)`
5. **验证数据注入** — 确认 `{{ ALL_DATA_JSON }}` 包含所有图表原始数据
6. **验证下载功能** — 确认 CSV 和 Excel 导出按钮功能正常
