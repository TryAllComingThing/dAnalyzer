# 华东区域周报

> 触发词: 华东周报 / 华东区域周报 / east weekly
> 路由: `Skill({skill: "danalyzer:recipe", args: "weekly-east"})`

## 数据源

### orders
- 注册名: `test_orders`
- 条件: area = '华东', 近 7 天

```sql
SELECT order_date, category, channel,
       SUM(actual_amount) AS sales,
       SUM(quantity)        AS volume,
       COUNT(DISTINCT order_id)   AS orders,
       COUNT(DISTINCT user_id)    AS users
FROM test_orders
WHERE area = '华东'
  AND order_date >= date('now', '-7 days')
GROUP BY order_date, category, channel
```

### users
- 注册名: `test_users`
- 条件: area = '华东', 近 7 天

```sql
SELECT register_date, vip_level,
       COUNT(DISTINCT user_id)    AS new_users,
       AVG(total_consume)         AS avg_ltv
FROM test_users
WHERE area = '华东'
  AND register_date >= date('now', '-7 days')
GROUP BY register_date, vip_level
```

## 指标

| code | 名称 | 来源 | 公式 | 格式化 |
|------|------|------|------|--------|
| total_sales | 销售额 | orders | `SUM(sales)` | `￥{:,.0f}` |
| total_orders | 订单量 | orders | `SUM(orders)` | `{:,}` |
| aov | 客单价 | orders | `total_sales / total_orders` | `￥{:,.2f}` |
| new_users | 新用户 | users | `SUM(new_users)` | `{:,}` |
| sales_wow | 环比 | orders | `(SUM(当日 sales) - SUM(7天前 sales)) / SUM(7天前 sales) * 100` | `{:+.1f}%` |
| top_category | 品类TOP1 | orders | `argmax(SUM(sales) BY category)` | 文本 |

## 输出

### KPI 卡片（一行四列）

```
total_sales  total_orders  aov  new_users
```

### 图表

| # | 类型 | 标题 | 数据 | x | y | 位置 |
|---|------|------|------|---|---|------|
| 1 | 折线 | 近 7 天销售趋势 | orders | order_date | sales, orders | row1, col1-2 |
| 2 | 饼图 | 品类占比 | orders | category | sales | row1, col3 |
| 3 | 柱状 | 渠道对比 | orders | channel | sales | row2, col1-2 |
| 4 | 折线 | 新用户趋势 | users | register_date | new_users | row2, col3 |

### 诊断

```
sales_wow > 10%  → "本周销售额环比增长 {sales_wow}，高于正常波动区间。主要贡献品类为 {top_category}。"
sales_wow < -10% → "⚠️ 本周销售额环比下降 {sales_wow}，需排查华东渠道及 {top_category} 品类是否存在缺货或活动断档。"
其他             → "本周销售额环比变化 {sales_wow}，整体平稳，{top_category} 仍为第一大品类。"
```

### 输出文件

```
output/weekly_report_east.html
```

## 红线

- SQL 不可修改（已固化的时间窗口和 WHERE 条件）
- 图表类型/维度不可替换
- 不可追加额外查询或数据源
- security 扫描不可跳过
