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
