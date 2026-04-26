# 组件库

## 概述

数据分析看板的图表组件库，包含各类可视化组件的配置和使用方法。

## 组件分类

### 1. 指标卡片 (KPI Card)

用于展示核心指标数值。

```yaml
component:
  type: kpi-card
  config:
    title: 今日销售额
    value: 125,680
    unit: 元
    prefix: ¥
    precision: 0
    trend: +15.8%
    trendDirection: up  # up/down/neutral
    icon: sales
    bgColor: gradient-blue
```

**配置字段**：
| 字段 | 说明 |
|------|------|
| title | 指标名称 |
| value | 数值 |
| unit | 单位 |
| prefix | 前缀符号 |
| precision | 小数位数 |
| trend | 趋势值 |
| trendDirection | 趋势方向 |

### 2. 趋势图表 (Trend Chart)

时间序列数据展示。

```yaml
component:
  type: trend-chart
  config:
    title: 销售额趋势
    xAxis: date
    yAxis: amount
    chartType: line  # line/area
    showArea: true
    smooth: true
    showDataLabel: false
    legend: true
    grid: true
```

### 3. 对比图表 (Comparison Chart)

分组对比数据展示。

```yaml
component:
  type: comparison-chart
  config:
    title: 各品类销售对比
    chartType: bar  # bar/histogram
    orientation: vertical  # vertical/horizontal
    showValue: true
    stack: false
    groupBy: category
```

### 4. 占比图表 (Proportion Chart)

构成分析展示。

```yaml
component:
  type: proportion-chart
  config:
    title: 销售占比
    chartType: pie  # pie/donut
    showPercent: true
    showLegend: true
    minPercent: 5  # 小于5%合并为其他
    centerLabel: 总计
```

### 5. 数据表格 (Data Table)

明细数据展示。

```yaml
component:
  type: data-table
  config:
    title: 销售明细
    columns:
      - field: product_name
        title: 商品名称
        width: 200
        sortable: true
      - field: sales_amount
        title: 销售额
        align: right
        format: currency
      - field: quantity
        title: 销量
        align: center
    pagination: true
    pageSize: 10
    sortable: true
    filterable: true
```

### 6. 排行榜 (Ranking)

Top N 排名展示。

```yaml
component:
  type: ranking
  config:
    title: 销售排行 Top 10
    rankField: rank
    valueField: sales_amount
    labelField: product_name
    showTrend: true
    showIndex: true
    topN: 10
```

### 7. 仪表盘 (Gauge)

目标完成率展示。

```yaml
component:
  type: gauge
  config:
    title: 目标完成率
    value: 78.5
    min: 0
    max: 100
    unit: '%'
    thresholds:
      - color: red
        max: 60
      - color: yellow
        max: 80
      - color: green
        max: 100
```

### 8. 漏斗图 (Funnel)

转化分析展示。

```yaml
component:
  type: funnel
  config:
    title: 用户转化漏斗
    stages:
      - name: 访问
        value: 10000
      - name: 注册
        value: 5000
      - name: 下单
        value: 2000
      - name: 支付
        value: 1500
    sort: desc
    labelPosition: right
```

### 9. 热力图 (Heatmap)

分布密度展示。

```yaml
component:
  type: heatmap
  config:
    title: 销售热力图
    xField: hour
    yField: dayOfWeek
    colorField: sales_amount
    colorScale: sequential
```

### 10. 地图 (Map)

地域分布展示。

```yaml
component:
  type: map
    config:
      title: 地域销售分布
      mapType: china
      regionField: province
      valueField: sales_amount
      showLabel: true
```

## 交互配置

所有组件支持以下交互：

| 交互 | 说明 | 配置 |
|------|------|------|
| 悬停提示 | Hover 显示详情 | `tooltip: true` |
| 点击跳转 | 点击跳转详情页 | `clickAction: navigate` |
| 筛选联动 | 筛选影响其他组件 | `linkage: true` |
| 缩放 | 支持缩放查看 | `zoom: true` |
| 下载 | 下载图表图片 | `download: true` |

## 通用配置

```yaml
component:
  type: trend-chart
  config:
    # 通用配置
    width: auto
    height: 300
    padding: 16
    theme: light  # light/dark
    loading: true
    emptyData: show  # show/hide/custom

    # 动画配置
    animation:
      enabled: true
      duration: 500
      easing: easeOutQuart

    # 响应式
    responsive: true
```

## 组件数据绑定

```yaml
dataBinding:
  type: api  # api/static/sql
  source: sales_trend_api
  refresh:
    enabled: true
    interval: 30  # 秒
    strategy: incremental  # incremental/full
  transform:
    - field: date
      type: date
      format: YYYY-MM-DD
    - field: amount
      type: number
      precision: 2
```

## 输出

- 组件配置 JSON
- 组件代码片段
- 数据绑定配置
- 交互事件配置
