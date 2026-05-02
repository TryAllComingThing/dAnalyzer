# 报告模板

## 周报模板

```markdown
# ${business_line} 周报 ${week}

## 一、本周概览

| 指标 | 本周 | 上周 | 环比 |
|------|------|------|------|
| 销售额 | ${sales_amount} | ${last_week_sales} | ${sales_growth}% |
| 订单量 | ${order_count} | ${last_week_orders} | ${order_growth}% |
| 客单价 | ${avg_order_amount} | ${last_week_avg} | ${avg_growth}% |

## 二、核心指标

### 2.1 销售指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 销售额 | ${sales_amount} | 同比${yoy_sales}% |
| 订单量 | ${order_count} | 同比${yoy_orders}% |
| 客单价 | ${avg_order_amount} | 同比${yoy_avg}% |

### 2.2 用户指标

| 指标 | 数值 | 环比 |
|------|------|------|
| 新增用户 | ${new_users} | ${new_user_growth}% |
| 活跃用户 | ${active_users} | ${active_user_growth}% |
| 复购率 | ${repurchase_rate}% | ${repurchase_growth}% |

## 三、核心发现

### 3.1 增长亮点
${growth_highlights}

### 3.2 异常预警
${abnormal_warnings}

## 四、问题分析

${problem_analysis}

## 五、下周建议

${next_week_suggestions}

---
报告生成时间：${report_time}
数据周期：${start_date} - ${end_date}
```

## 月报模板

```markdown
# ${business_line} 月报 ${month}

## 一、本月概览

| 指标 | 本月 | 上月 | 环比 | 去年同期 | 同比 |
|------|------|------|------|----------|------|
| 销售额 | ${sales} | ${last_month} | ${mom}% | ${last_year} | ${yoy}% |
| 订单量 | ${orders} | - | ${mom_orders}% | - | ${yoy_orders}% |
| 客单价 | ${avg} | - | ${mom_avg}% | - | ${yoy_avg}% |

## 二、核心指标

### 2.1 销售趋势
${sales_trend_chart}

### 2.2 渠道分析

| 渠道 | 销售额 | 占比 | 环比 |
|------|--------|------|------|
| APP | ${app_sales} | ${app_pct}% | ${app_growth}% |
| 小程序 | ${mini_app_sales} | ${mini_pct}% | ${mini_growth}% |
| Web | ${web_sales} | ${web_pct}% | ${web_growth}% |

### 2.3 商品分析

#### 热销商品 TOP5
${top_products}

#### 滞销商品
${slow_moving}

## 三、用户分析

### 3.1 用户规模
- 新增用户：${new_users}
- 活跃用户：${active_users}
- 累计用户：${total_users}

### 3.2 用户留存
- 次日留存：${d1_retention}%
- 7日留存：${d7_retention}%
- 30日留存：${d30_retention}%

## 四、问题与机会

### 4.1 问题
${problems}

### 4.2 机会
${opportunities}

## 五、下月计划

${next_month_plan}

---
报告生成时间：${report_time}
数据周期：${start_date} - ${end_date}
```

## 关键占位符说明

| 占位符 | 说明 | 示例 |
|--------|------|------|
| ${business_line} | 业务线 | 电商、线下 |
| ${week} | 周次 | 2026年第17周 |
| ${month} | 月份 | 2026年4月 |
| ${start_date} | 开始日期 | 2026-04-21 |
| ${end_date} | 结束日期 | 2026-04-27 |
| ${sales_amount} | 销售额 | 1,000,000 |
| ${order_count} | 订单量 | 10,000 |
| ${avg_order_amount} | 客单价 | 100.00 |
| ${growth_pct} | 增长率 | 15% |
