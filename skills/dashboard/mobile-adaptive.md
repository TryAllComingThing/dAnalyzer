# 移动端适配

## 概述

配置看板在移动端的响应式布局和交互优化。

## 断点配置

```yaml
breakpoints:
  xs:
    min: 0
    max: 479
    columns: 1
    label: 手机
  sm:
    min: 480
    max: 767
    columns: 2
    label: 大手机
  md:
    min: 768
    max: 1023
    columns: 2
    label: 平板
  lg:
    min: 1024
    max: 1279
    columns: 3
    label: 小屏电脑
  xl:
    min: 1280
    max: 1535
    columns: 4
    label: 电脑
  xxl:
    min: 1536
    max: null
    columns: 4
    label: 大屏
```

## 布局适配

### 1. 移动端布局转换

桌面端多列布局 → 移动端单列堆叠

```yaml
layout:
  desktop:
    rows: 3
    cols: 4
    areas:
      - name: kpi
        col: 1
        row: 1
        colSpan: 4
      - name: trend
        col: 1
        row: 2
        colSpan: 2
      - name: chart1
        col: 3
        row: 2
        colSpan: 2
      - name: table
        col: 1
        row: 3
        colSpan: 4

  mobile:
    direction: vertical  # vertical/horizontal
    stackOrder: [kpi, trend, chart1, table]
    spacing: 12px
```

### 2. 组件自适应

```yaml
components:
  kpiCard:
    desktop:
      layout: horizontal
      showIcon: true
      showTrend: true
    mobile:
      layout: vertical
      showIcon: false
      showTrend: true

  chart:
    desktop:
      height: 300
      showLegend: true
      showDataZoom: true
    mobile:
      height: 250
      showLegend: false
      showDataZoom: false

  table:
    desktop:
      pagination: true
      pageSize: 10
      scrollable: true
      columns: 5
    mobile:
      pagination: false
      scrollable: true
      columns: 3
      stickyHeader: true
```

## 交互优化

### 手势支持

```yaml
gestures:
  enabled: true
  types:
    - name: swipe
      action: navigate  # navigate/switchPage/scroll
      direction: left  # left/right/up/down
    - name: pinch
      action: zoom
      minScale: 0.5
      maxScale: 3
    - name: longPress
      action: contextMenu
      duration: 500
    - name: pullRefresh
      action: reload
      distance: 50
```

### 触摸优化

```yaml
touch:
  tapHighlight: false
  touchAction: manipulation
  minTapArea: 44px  # 最小点击区域
  swipeThreshold: 30px
  velocityThreshold: 0.3
```

## 性能优化

### 懒加载

```yaml
lazyLoad:
  enabled: true
  threshold: 200  # 预加载距离
  strategy: viewport  # viewport/onInteraction
  components:
    - type: chart
      strategy: onInteraction
    - type: table
      strategy: onInteraction
```

### 图片优化

```yaml
imageOptimization:
  enabled: true
  formats:
    desktop: [svg, png]
    mobile: [webp, avif]
  sizes:
    - 640  # 2x
    - 320  # 1x
  lazy: true
```

### 数据量控制

```yaml
dataOptimization:
  mobile:
    maxTableRows: 50
    maxChartPoints: 100
    aggregation: auto
    chartSampling: true
    samplingMethod: LTTB
```

## 移动端特定组件

### 1. 指标卡简化

```yaml
kpiCard:
  mobile:
    simplified: true
    showSparkline: true
    tapAction: expand  # expand/navigate/modal
```

### 2. 图表简化

```yaml
chart:
  mobile:
    simplified: true
    hideLegend: true
    hideAxisLabels: true
    showTooltips: true
```

### 3. 移动端导航

```yaml
navigation:
  type: tabBar  # tabBar/drawer/singlePage
  tabBar:
    position: bottom
    items:
      - label: 概览
        icon: dashboard
        route: /
      - label: 趋势
        icon: chart
        route: /trend
      - label: 明细
        icon: table
        route: /table
      - label: 我的
        icon: user
        route: /profile
    activeColor: "#4264F5"
```

## 响应式图表

```yaml
responsiveChart:
  enabled: true
  config:
    aspectRatio:
      mobile: 1.5
      tablet: 2
      desktop: null  # auto
    margins:
      mobile: [10, 10, 30, 10]
      desktop: [20, 20, 60, 40]
    label:
      mobile:
        fontSize: 10
        rotation: 45
      desktop:
        fontSize: 12
        rotation: 0
```

## 输出

- 响应式布局配置
- 移动端组件代码
- 手势交互代码
- 性能优化代码
- 移动端导航代码
