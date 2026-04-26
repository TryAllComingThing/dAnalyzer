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

## 输入参数

| 参数 | 说明 | 必填 | 示例 |
|------|------|------|------|
| dashboard_name | 看板名称 | 是 | "销售数据看板" |
| charts | 图表配置数组 | 是 | 见下方格式 |
| layout | 布局配置 | 否 | grid//free |
| theme | 主题风格 | 否 | light/dark/blue |
| responsive | 自适应 | 否 | true |
| refresh_interval | 刷新间隔(秒) | 否 | 30 |

### charts 数据格式

```json
{
  "charts": [
    {
      "id": "kpi_1",
      "type": "kpi",
      "title": "今日销售额",
      "data_source": "data-query",
      "query": "查询今日销售额",
      "position": {"x": 0, "y": 0, "w": 3, "h": 1}
    },
    {
      "id": "trend_1",
      "type": "line",
      "title": "销售趋势",
      "data_source": "data-query",
      "query": "查询近7天销售数据",
      "chart_type": "line",
      "position": {"x": 0, "y": 1, "w": 8, "h": 3}
    },
    {
      "id": "compare_1",
      "type": "bar",
      "title": "各品类销售对比",
      "data_source": "data-query",
      "query": "查询各品类销售数据",
      "chart_type": "bar",
      "position": {"x": 0, "y": 4, "w": 4, "h": 3}
    },
    {
      "id": "pie_1",
      "type": "pie",
      "title": "品类占比",
      "data_source": "data-query",
      "query": "查询品类占比",
      "chart_type": "pie",
      "position": {"x": 4, "y": 4, "w": 4, "h": 3}
    }
  ]
}
```

### layout 布局配置

```json
{
  "layout": "grid",
  "cols": 12,
  "row_height": 100,
  "margin": [10, 10],
  "container_padding": [20, 20]
}
```

## 执行流程

```
┌─────────────────────────────────────────────────────────────┐
│                     dashboard 技能                          │
├─────────────────────────────────────────────────────────────┤
│  输入：dashboard_name + charts + layout                       │
│                     │                                        │
│                     ▼                                        │
│         ┌─────────────────────┐                              │
│         │ 1. 需求理解          │                              │
│         │ - 看板用途           │                              │
│         │ - 图表数量           │                              │
│         │ - 布局方式           │                              │
│         └──────────┬──────────┘                              │
│                    │                                        │
│                    ▼                                        │
│         ┌─────────────────────┐                              │
│         │ 2. 数据查询          │                              │
│         │ 对每个图表调用        │                              │
│         │ data-query 技能      │                              │
│         └──────────┬──────────┘                              │
│                    │                                        │
│                    ▼                                        │
│         ┌─────────────────────┐                              │
│         │ 3. 图表生成          │                              │
│         │ 调用 visual 技能     │                              │
│         │ 生成 ECharts 配置    │                              │
│         └──────────┬──────────┘                              │
│                    │                                        │
│                    ▼                                        │
│         ┌─────────────────────┐                              │
│         │ 4. 布局编排          │                              │
│         │ - 网格布局计算       │                              │
│         │ - 组件位置确定       │                              │
│         │ - 响应式断点设置      │                              │
│         └──────────┬──────────┘                              │
│                    │                                        │
│                    ▼                                        │
│         ┌─────────────────────┐                              │
│         │ 5. HTML生成          │                              │
│         │ - 完整页面结构        │                              │
│         │ - ECharts集成         │                              │
│         │ - CSS样式            │                              │
│         │ - 响应式适配          │                              │
│         └──────────┬──────────┘                              │
│                    │                                        │
│                    ▼                                        │
│         ┌─────────────────────┐                              │
│         │ 6. 实时/告警配置     │                              │
│         │ (可选)               │                              │
│         └──────────┬──────────┘                              │
│                    │                                        │
│                    ▼                                        │
│              ┌─────────────┐                                │
│              │ 输出HTML文件 │                                │
│              └─────────────┘                                │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: 需求理解

```
输入示例:
{
  "dashboard_name": "销售数据看板",
  "charts": [
    {"type": "kpi", "title": "今日销售额"},
    {"type": "line", "title": "销售趋势"},
    {"type": "bar", "title": "品类对比"},
    {"type": "pie", "title": "品类占比"}
  ]
}

分析:
- 看板类型: 销售监控
- 图表数量: 4个
- 布局: 2行2列
- 需调用 data-query: 4次
- 需调用 visual: 4次
```

### Step 2: 数据查询

```
并行调用 data-query 技能:
- KPI数据查询
- 趋势数据查询
- 对比数据查询
- 占比数据查询

每个查询结果返回:
{
  "data": {...},
  "sql": "SELECT ...",
  "row_count": 100
}
```

### Step 3: 图表生成

```
对每个数据调用 visual 技能生成 ECharts 配置:
- KPI卡片 → 数值展示
- 趋势数据 → 折线图配置
- 对比数据 → 柱状图配置
- 占比数据 → 饼图配置

返回每个图表的 ECharts option 对象
```

### Step 4: 布局编排

```
网格布局计算 (12列):
- KPI卡片: col-span=3
- 趋势图: col-span=8
- 对比图: col-span=4
- 占比图: col-span=4

响应式断点:
- PC: > 1200px (4列)
- 平板: 768px-1200px (2列)
- 手机: < 768px (1列)
```

### Step 5: HTML生成 ⭐

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>销售数据看板</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; }
    .dashboard { max-width: 1400px; margin: 0 auto; padding: 20px; }
    .dashboard-header { margin-bottom: 20px; }
    .dashboard-header h1 { font-size: 24px; color: #333; }
    .dashboard-header .subtitle { font-size: 14px; color: #666; margin-top: 5px; }
    .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 20px; }
    .card { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .kpi-card { text-align: center; }
    .kpi-value { font-size: 32px; font-weight: bold; color: #1890ff; }
    .kpi-label { font-size: 14px; color: #666; margin-top: 8px; }
    .kpi-trend { font-size: 12px; margin-top: 8px; }
    .kpi-trend.up { color: #52c41a; }
    .kpi-trend.down { color: #f5222d; }
    .chart-container { width: 100%; height: 300px; }
    
    /* 响应式 */
    @media (max-width: 1200px) { .grid { grid-template-columns: repeat(4, 1fr); } }
    @media (max-width: 768px) {
      .grid { grid-template-columns: 1fr; }
      .dashboard { padding: 10px; }
      .dashboard-header h1 { font-size: 18px; }
      .kpi-value { font-size: 24px; }
    }
  </style>
</head>
<body>
  <div class="dashboard">
    <div class="dashboard-header">
      <h1>销售数据看板</h1>
      <div class="subtitle">数据更新于 2026-04-25 10:30:00</div>
    </div>
    <div class="grid">
      <!-- KPI 1 -->
      <div class="card kpi-card" style="grid-column: span 3">
        <div class="kpi-value">¥128,500</div>
        <div class="kpi-label">今日销售额</div>
        <div class="kpi-trend up">↑ 12.5% 较昨日</div>
      </div>
      <!-- KPI 2 -->
      <div class="card kpi-card" style="grid-column: span 3">
        <div class="kpi-value">1,256</div>
        <div class="kpi-label">今日订单</div>
        <div class="kpi-trend up">↑ 8.3% 较昨日</div>
      </div>
      <!-- KPI 3 -->
      <div class="card kpi-card" style="grid-column: span 3">
        <div class="kpi-value">356</div>
        <div class="kpi-label">今日访客</div>
        <div class="kpi-trend down">↓ 2.1% 较昨日</div>
      </div>
      <!-- KPI 4 -->
      <div class="card kpi-card" style="grid-column: span 3">
        <div class="kpi-value">28.3%</div>
        <div class="kpi-label">转化率</div>
        <div class="kpi-trend up">↑ 1.2% 较昨日</div>
      </div>
      <!-- 趋势图 -->
      <div class="card" style="grid-column: span 8">
        <div class="chart-container" id="chart_trend"></div>
      </div>
      <!-- 占比图 -->
      <div class="card" style="grid-column: span 4">
        <div class="chart-container" id="chart_pie"></div>
      </div>
      <!-- 对比图 -->
      <div class="card" style="grid-column: span 6">
        <div class="chart-container" id="chart_bar"></div>
      </div>
      <!-- 表格 -->
      <div class="card" style="grid-column: span 6">
        <div class="chart-container" id="chart_table"></div>
      </div>
    </div>
  </div>
  <script>
    // ECharts 实例初始化
    var chartTrend = echarts.init(document.getElementById('chart_trend'));
    var chartPie = echarts.init(document.getElementById('chart_pie'));
    var chartBar = echarts.init(document.getElementById('chart_bar'));
    
    // 配置赋值
    chartTrend.setOption({ /* 趋势图配置 */ });
    chartPie.setOption({ /* 饼图配置 */ });
    chartBar.setOption({ /* 柱图配置 */ });
    
    // 响应式
    window.addEventListener('resize', function() {
      chartTrend.resize();
      chartPie.resize();
      chartBar.resize();
    });
  </script>
</body>
</html>
```

## 输出结果

```json
{
  "status": "success",
  "dashboard": {
    "name": "销售数据看板",
    "file": "output/dashboard_sales_20260425.html",
    "charts_count": 6,
    "responsive": true
  },
  "metadata": {
    "format": "html",
    "size": "45KB",
    "echarts_version": "5.4.3",
    "created_at": "2026-04-25 10:30:00"
  }
}
```

## 使用示例

### 示例1: 销售监控看板
```
用户: 生成一个销售数据看板，包含今日销售额、订单数、转化率，以及销售趋势图、各品类占比图

输入:
{
  "dashboard_name": "销售数据看板",
  "charts": [
    {"id": "kpi_sales", "type": "kpi", "title": "今日销售额", "query": "查询今日销售额"},
    {"id": "kpi_orders", "type": "kpi", "title": "今日订单", "query": "查询今日订单数"},
    {"id": "kpi_rate", "type": "kpi", "title": "转化率", "query": "查询今日转化率"},
    {"id": "trend_sales", "type": "line", "title": "销售趋势", "query": "查询近7天销售趋势"},
    {"id": "pie_category", "type": "pie", "title": "品类占比", "query": "查询各品类销售占比"}
  ],
  "layout": "grid",
  "responsive": true
}

执行流程:
1. data-query 查询5组数据
2. visual 生成各图表 ECharts 配置
3. 组装 HTML 页面（KPI卡片 + 趋势图 + 饼图）
4. 输出完整 HTML 看板

输出:
- dashboard_sales_20260425.html
- 包含4个KPI卡片 + 1个趋势图 + 1个饼图
- 支持PC/手机自适应
```

### 示例2: 用户分析看板
```
输入:
{
  "dashboard_name": "用户分析看板",
  "charts": [
    {"type": "kpi", "title": "总用户数", "query": "查询总用户数"},
    {"type": "kpi", "title": "新增用户", "query": "查询本月新增用户"},
    {"type": "line", "title": "用户增长趋势", "query": "查询用户增长趋势"},
    {"type": "bar", "title": "渠道用户对比", "query": "查询各渠道用户数"},
    {"type": "heatmap", "title": "活跃时段分布", "query": "查询用户活跃时段"}
  ]
}
```

## 子技能

| 子技能 | 文件 | 说明 |
|--------|------|------|
| 看板布局 | layout-config.md | 页面布局配置 |
| 组件库 | component-lib.md | 图表组件库 |
| 实时数据 | real-time-data.md | 实时数据同步 |
| 告警规则 | alert-rules.md | 告警阈值配置 |
| 主题定制 | theme-custom.md | 主题样式 |
| 移动端适配 | mobile-adaptive.md | 响应式布局 |
| 导出分享 | export-share.md | 导出与分享 |

## 依赖配置

- skills/data-query - 数据查询
- skills/data-analysis - 数据分析
- skills/visual - 可视化（ECharts）
- skills/report - 报告导出
- skills/security - 安全脱敏（输出前处理）
- rules/core/indicator-caliber.md - 指标口径
- data/template/dashboard-layout.md - 布局模板
- ECharts CDN: https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js
