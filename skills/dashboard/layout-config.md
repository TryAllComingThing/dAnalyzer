# 看板布局配置

## 概述

定义看板的页面布局结构，包括网格系统、区域划分、响应式布局等。

## 布局类型

### 1. 网格布局 (Grid)

```
┌─────┬─────┬─────┐
│ KPI │ KPI │ KPI │
├─────┼─────┼─────┤
│ 图表 │ 图表 │ 图表 │
├─────┴─────┼─────┤
│   表格    │ 详情 │
└───────────┴─────┘
```

配置示例：
```yaml
layout:
  type: grid
  rows: 4
  cols: 4
  gap: 16px
  areas:
    - name: header
      row: 1
      col: 1
      rowSpan: 1
      colSpan: 4
      components: [kpi-card, kpi-card, kpi-card, kpi-card]
    - name: trend
      row: 2
      col: 1
      rowSpan: 2
      colSpan: 2
      components: [trend-chart]
    - name: detail
      row: 2
      col: 3
      rowSpan: 2
      colSpan: 2
      components: [table]
```

### 2. 自由布局 (Free)

- 拖拽式组件摆放
- 绝对定位
- 支持任意尺寸

### 3. 瀑布布局 (Waterfall)

- 自适应高度
- 自动排列
- 适合移动端

## 布局配置字段

| 字段 | 类型 | 说明 | 必填 |
|------|------|------|------|
| type | string | 布局类型: grid/free/waterfall | ✅ |
| rows | number | 行数 (grid) | ✅ |
| cols | number | 列数 (grid) | ✅ |
| gap | number | 间距 (px) | ✅ |
| areas | array | 区域配置 | ✅ |
| minHeight | number | 最小高度 | ❌ |
| padding | number | 内边距 | ❌ |

## 区域配置

```yaml
areas:
  - name: main
    row: 1
    col: 1
    rowSpan: 2
    colSpan: 2
    components:
      - type: trend-chart
        dataSource: sales_trend
        config:
          title: 销售趋势
          height: 300
```

## 响应式断点

| 断点 | 屏幕宽度 | 列数 |
|------|----------|------|
| desktop | ≥1200px | 4 |
| tablet | 768-1199px | 2 |
| mobile | <768px | 1 |

## 主题支持

- 深色模式
- 浅色模式
- 企业主题

## 输出

- 布局配置 JSON
- 响应式样式
- 预览效果
