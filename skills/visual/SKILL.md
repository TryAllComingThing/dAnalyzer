---
name: visual
description: 可视化技能，支持ECharts图表生成、趋势图、对比图、分布图、占比图、热力图、仪表盘、HTML自适应多端输出、数据查看与下载
---

# 可视化技能 (Visual)

## When to Activate

- Use this skill when creating visualizations or charts
- Use this skill when generating trend charts or line charts
- Use this skill when creating comparison charts or bar charts
- Use this skill when building distribution charts or histograms
- Use this skill when generating pie charts or proportion charts
- Use this skill when creating heatmaps or correlation matrices
- Use this skill when configuring dashboards
- Use this skill when user wants HTML output for web or mobile display
- Use this skill when need responsive charts that adapt to different screen sizes
- Use this skill when user wants to view or download the underlying data

---

## ⚠️ 数据读写强制使用 Connector

**生成 HTML 前必须通过 Connector 读取分析结果，禁止用 `open()` / `json.load()` 裸读**。

```python
# ✅ 正确: 使用 JSONConnector 读取 data-analysis 的分析结果
from connectors.tool.json_connector import JSONConnector
jc = JSONConnector()
result = jc.read('output/data_analysis_result.json')
analysis_data = result.raw_data

# ✅ 正确: 使用 CSVConnector 读取原始数据
from connectors.tool.csv_connector import CSVConnector
cc = CSVConnector()
result = cc.read('output/query_result.csv')

# ❌ 错误: import json; json.load(open('file.json'))
# ❌ 错误: import csv; csv.DictReader(open('file.csv'))
```

**写入输出文件也走 Connector**:

```python
# 写 CSV 供下载
from connectors.tool.csv_connector import CSVConnector
cc = CSVConnector()
cc.write(data_list, 'output/export.csv')

# 写 Excel 供下载
from connectors.tool.excel_connector import ExcelConnector
ec = ExcelConnector()
ec.write(data_list, 'output/export.xlsx')
```

---

## 核心能力

1. **ECharts集成** ⭐ — 完整ECharts配置，生成交互式HTML图表
2. **自适应多端** ⭐ — 输出HTML自动适配PC/平板/手机
3. **数据交互** ⭐ — 点击查看明细、查看原始数据、下载数据
4. **趋势图** — 折线图、面积图
5. **对比图** — 柱状图、条形图
6. **分布图** — 直方图、箱线图
7. **占比图** — 饼图、环形图
8. **热力图** — 颜色热力图
9. **仪表盘** — 可视化仪表盘

---

## 数据交互设计

### 分层交互

```
图表区域                        数据操作区
┌──────────────────────┐    ┌─────────────────────────┐
│                      │    │ [查看数据] [下载CSV]    │
│      📈 图表        │    │ [下载Excel] [下载JSON]  │
│                      │    └─────────────────────────┘
│  悬停 → tooltip      │
│  点击 → 数据详情弹窗  │         ↓
└──────────────────────┘    展开 → 数据表格 / 下载文件
```

### 1. 悬停 Tooltip（轻量级）

- **触发**：鼠标悬停在数据点上
- **显示**：数值、时间、同比/环比
- **示例**：ECharts 自带 tooltip，无需额外配置

```javascript
tooltip: {
  trigger: 'axis',
  formatter: function(params) {
    // 显示数值和变化
  }
}
```

### 2. 点击查看数据详情（中等）

- **触发**：点击图表中的数据点
- **显示**：弹出面板，展示该数据点的完整字段

```javascript
// 点击事件配置
chart.on('click', function(params) {
  // 显示数据详情弹窗
  showDetailPanel(params.data);
});
```

**详情面板内容**：
```html
<div class="detail-panel">
  <h3>2026年4月 销售数据</h3>
  <table>
    <tr><td>销售额</td><td>125,680</td></tr>
    <tr><td>订单数</td><td>1,256</td></tr>
    <tr><td>客单价</td><td>100.06</td></tr>
    <tr><td>环比</td><td>+15.8%</td></tr>
    <tr><td>同比</td><td>+25.3%</td></tr>
  </table>
</div>
```

### 3. 查看原始数据（完整）

- **触发**：点击"查看数据"按钮
- **显示**：展开数据表格，支持分页

```html
<!-- 数据查看区域 -->
<div class="data-panel" id="dataPanel">
  <div class="panel-header">
    <h3>📊 原始数据</h3>
    <button class="close-btn" onclick="toggleDataPanel()">×</button>
  </div>
  <div class="table-container">
    <table class="data-table">
      <thead>
        <tr>
          <th>日期</th>
          <th>销售额</th>
          <th>订单数</th>
          <th>客单价</th>
          <th>环比</th>
        </tr>
      </thead>
      <tbody>
        <!-- 分页加载 -->
      </tbody>
    </table>
  </div>
  <div class="pagination">
    <button>上一页</button>
    <span>1 / 10</span>
    <button>下一页</button>
  </div>
</div>
```

### 4. 下载数据（导出）

- **触发**：点击下载按钮
- **支持**：CSV、Excel、JSON 三种格式

```html
<!-- 下载按钮区域 -->
<div class="download-panel">
  <button class="btn-download" onclick="downloadData('csv')">
    📥 下载CSV
  </button>
  <button class="btn-download" onclick="downloadData('excel')">
    📥 下载Excel
  </button>
  <button class="btn-download" onclick="downloadData('json')">
    📥 下载JSON
  </button>
</div>
```

---

## 输入参数

| 参数 | 说明 | 必填 | 示例 |
|------|------|------|------|
| chart_type | 图表类型 | 是 | line/bar/pie/heatmap/gauge |
| data | 图表数据 | 是 | 见下方data格式 |
| title | 图表标题 | 否 | "2026年销售额趋势" |
| x_axis | X轴字段 | 视图表类型 | "date" |
| y_axis | Y轴字段 | 视图表类型 | "gmv" |
| output_format | 输出格式 | 否 | html/png/json |
| responsive | 是否自适应 | 否 | true |
| enable_data_interaction | 启用数据交互 | 否 | true |
| enable_download | 启用数据下载 | 否 | true |

### data 数据格式

```json
{
  "x_data": ["2026-01", "2026-02", "2026-03", "2026-04"],
  "series": [
    {"name": "销售额", "data": [100, 120, 150, 180]},
    {"name": "订单量", "data": [50, 60, 75, 90]}
  ],
  "dimensions": ["x", "sales", "orders"],
  "raw_data": [  // 完整原始数据（用于查看/下载）
    {"date": "2026-01", "sales": 100, "orders": 50},
    {"date": "2026-02", "sales": 120, "orders": 60}
  ],
  "metadata": {
    "fields": ["date", "sales", "orders"],
    "total_rows": 100,
    "update_time": "2026-04-25 10:00:00"
  }
}
```

---

## 输出结果

### 完整 HTML 输出（推荐）

```json
{
  "status": "success",
  "chart": {
    "type": "line",
    "title": "2026年销售额趋势",
    "file": "output/chart_sales_trend_20260425.html",
    "responsive": true
  },
  "data_interaction": {
    "tooltip": true,
    "click_detail": true,
    "view_raw_data": true,
    "download": {
      "csv": true,
      "excel": true,
      "json": true
    }
  },
  "data": {
    "raw_data": [...],
    "metadata": {
      "total_rows": 100,
      "fields": ["date", "sales", "orders"]
    },
    "download_files": {
      "csv": "output/sales_trend_20260425.csv",
      "excel": "output/sales_trend_20260425.xlsx",
      "json": "output/sales_trend_20260425.json"
    }
  },
  "metadata": {
    "format": "html",
    "size": "15KB",
    "echarts_version": "5.4.3"
  }
}
```

---

## 执行流程

```
┌─────────────────────────────────────────────────────────────┐
│                      visual 技能                            │
├─────────────────────────────────────────────────────────────┤
│  输入：chart_type + data + enable_data_interaction           │
│                     │                                        │
│                     ▼                                        │
│         ┌─────────────────────┐                            │
│         │ 1. 选择图表类型      │                            │
│         └──────────┬──────────┘                            │
│                    │                                        │
│                    ▼                                        │
│         ┌─────────────────────┐                            │
│         │ 2. 生成ECharts配置   │                            │
│         │ + 数据交互配置       │  ← 新增                    │
│         └──────────┬──────────┘                            │
│                    │                                        │
│                    ▼                                        │
│         ┌─────────────────────┐                            │
│         │ 3. 生成HTML(含数据)  │                            │
│         │ - 图表区域           │                            │
│         │ - 数据操作区         │  ← 新增                    │
│         │ - 弹窗/表格模板      │  ← 新增                    │
│         └──────────┬──────────┘                            │
│                    │                                        │
│                    ▼                                        │
│              ┌─────────────┐                                │
│              │ [REVIEWER]  │                                │
│              │ 图表规范校验 │                                │
│              └──────┬──────┘                                │
│                      │                                        │
│              ┌───────┴───────┐                              │
│              ▼               ▼                              │
│           校验通过          校验失败                          │
│              │               │                              │
│              ▼               ▼                              │
│         输出图表文件       重新生成                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 使用示例

### 示例1: 带数据交互的趋势图

```
用户: 画一个销售额趋势图，并支持查看和下载数据

输入:
{
  "chart_type": "line",
  "data": {
    "x_data": ["1月", "2月", "3月", "4月"],
    "series": [
      {"name": "销售额", "data": [100, 120, 150, 180]}
    ],
    "raw_data": [
      {"month": "1月", "sales": 100, "orders": 50},
      {"month": "2月", "sales": 120, "orders": 60},
      {"month": "3月", "sales": 150, "orders": 75},
      {"month": "4月", "sales": 180, "orders": 90}
    ]
  },
  "title": "2026年各月销售额趋势",
  "output_format": "html",
  "enable_data_interaction": true,
  "enable_download": true
}

输出:
- HTML文件: chart_sales_trend.html
  ├─ 图表区域（ECharts）
  ├─ 悬停tooltip（数值显示）
  ├─ 点击弹窗（数据详情）
  ├─ 数据操作区
  │   ├─ 查看原始数据 → 分页表格
  │   ├─ 下载CSV
  │   ├─ 下载Excel
  │   └─ 下载JSON
```

### 示例2: 多系列对比图

```
输入:
{
  "chart_type": "bar",
  "data": {
    "x_data": ["华东", "华南", "华北", "西南"],
    "series": [
      {"name": "本月", "data": [100, 80, 60, 40]},
      {"name": "上月", "data": [90, 70, 55, 35]}
    ],
    "raw_data": [
      {"region": "华东", "this_month": 100, "last_month": 90},
      {"region": "华南", "this_month": 80, "last_month": 70}
    ]
  },
  "title": "各区域销售对比",
  "output_format": "html",
  "enable_download": true
}
```

---

## 数据下载格式示例

### CSV 格式
```csv
日期,销售额,订单数,客单价,环比
2026-01,100000,1000,100,-
2026-02,120000,1200,100,+20%
```

### Excel 格式
- 包含明细 Sheet
- 格式化表头
- 支持大数据量

### JSON 格式
```json
{
  "metadata": {
    "generated_at": "2026-04-25T10:00:00Z",
    "total_rows": 100,
    "fields": ["date", "sales", "orders"]
  },
  "data": [
    {"date": "2026-01", "sales": 100, "orders": 1000}
  ]
}
```

---

## 子技能

| 子技能 | 文件 | 说明 |
|--------|------|------|
| 图表规范 | chart-standard.md | 图表标准 |
| 对比图 | comparison-chart.md | 对比可视化 |
| 仪表盘 | dashboard-config.md | 仪表盘配置 |
| 分布图 | distribution-chart.md | 分布可视化 |
| 热力图 | heatmap-gen.md | 热力图生成 |
| 占比图 | proportion-chart.md | 占比可视化 |
| 趋势图 | trend-chart.md | 趋势可视化 |

---

## 依赖配置

### Connector 模块（强制使用 — 数据读写必须走 Connector）

| 操作 | 导入路径 |
|------|---------|
| 读 CSV | `from connectors.tool.csv_connector import CSVConnector` |
| 读 JSON | `from connectors.tool.json_connector import JSONConnector` |
| 写 Excel | `from connectors.tool.excel_connector import ExcelConnector` |

**禁止**用 `import csv` / `json.load(open())` / `open().write()` 裸读写数据文件。

- skills/data-query - 数据查询
- skills/data-clean - 数据清洗
- rules/base/chart-standard.md - 图表规范
- ECharts CDN: https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js

---

## 注意事项

1. **数据安全**：下载数据需经过 security 技能脱敏处理
2. **大数据量**：超过1万行建议分页加载或提示用户
3. **权限控制**：敏感数据需检查权限后才能下载
4. **文件大小**：Excel导出有行数限制，建议分Sheet
