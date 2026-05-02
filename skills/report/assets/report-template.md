# 报告模板

> 模板段落标题与 SKILL.md 报告类型表名称精确对应。Claude 按类型名直接定位段落，不做模糊匹配。

---

## 数据来源映射

**填充模板前，先按此表将上游数据列映射到占位符：**

| 占位符 | 来源技能 | 典型列名 | 说明 |
|--------|---------|---------|------|
| `${business_line}` | 用户输入 | — | 业务线名称 |
| `${date_range}` | danalyzer-core | — | 数据周期（格式见下方规范） |
| `${report_time}` | 系统 | — | 生成时间 YYYY-MM-DD HH:MM |
| `${total_sales}` | data-query | `sales`, `total_sales`, `SUM(amount)` | 本期销售额（千分位） |
| `${prev_sales}` | data-query | `prev_sales`, `last_period_sales` | 上期销售额 |
| `${sales_growth}` | data-analysis | `growth`, `sales_growth` | 销售增长率（%，保留 1 位） |
| `${total_orders}` | data-query | `orders`, `order_count`, `COUNT(id)` | 本期订单量 |
| `${prev_orders}` | data-query | `prev_orders`, `last_period_orders` | 上期订单量 |
| `${order_growth}` | data-analysis | `order_growth` | 订单增长率（%） |
| `${avg_order}` | data-analysis | `avg_order`, `aov` | 客单价 |
| `${prev_avg}` | data-analysis | `prev_avg`, `last_period_avg` | 上期客单价 |
| `${avg_growth}` | data-analysis | `avg_growth` | 客单价增长率（%） |
| `${new_users}` | data-query | `new_users`, `new_user_count` | 新增用户数 |
| `${active_users}` | data-query | `active_users`, `dau`, `mau` | 活跃用户数 |
| `${repurchase_rate}` | data-analysis | `repurchase_rate`, `rebuy_rate` | 复购率（%） |
| `${d1}` `${d7}` `${d30}` | model | `d1_retention`, `d7_retention`, `d30_retention` | 留存率（%） |
| `${summary}` | Claude 综合 | — | 一段话摘要 |
| `${highlights}` | Claude 综合 | — | 增长亮点 |
| `${anomalies}` | data-analysis + Claude | — | 异常检测结果 + 解读 |
| `${attention}` | Claude 综合 | — | 关注事项/建议 |
| `${insights}` | Claude 综合 | — | 分析洞察/原因/结论 |
| `${trend_chart}` | visual | — | `![标题](output/chart_xxx.png)` |

**图表约定：** 报告输出 Markdown，图表由 visual 技能预先生成为 PNG/SVG 文件。占位符填入 Markdown 图片语法：

```markdown
![2026年第18周销售趋势](output/sales_trend_w18.png)
```

**自由文本占位符**（`${summary}` `${highlights}` `${anomalies}` `${attention}` `${insights}`）由 Claude 根据数据分析结果撰写，不来自单一数据列。

---

## 日报

```markdown
# ${business_line} 日报 ${date_range}

## 一、今日概览

| 指标 | 今日 | 昨日 | 环比 |
|------|------|------|------|
| 销售额 | ${total_sales} | ${prev_sales} | ${sales_growth}% |
| 订单量 | ${total_orders} | ${prev_orders} | ${order_growth}% |
| 客单价 | ${avg_order} | ${prev_avg} | ${avg_growth}% |

## 二、实时数据

- 当前销售额：${current_sales}（截至 ${current_time}）
- 今日目标：${sales_target} / 达成率 ${target_rate}%

## 三、核心指标趋势

${trend_chart}

## 四、异常预警

${anomalies}

## 五、关注事项

${attention}

---
报告生成时间：${report_time}
数据日期：${date_range}
```

---

## 周报

```markdown
# ${business_line} 周报 ${date_range}

## 一、本周摘要

${summary}

## 二、核心指标

| 指标 | 本周 | 上周 | 环比 |
|------|------|------|------|
| 销售额 | ${total_sales} | ${prev_sales} | ${sales_growth}% |
| 订单量 | ${total_orders} | ${prev_orders} | ${order_growth}% |
| 客单价 | ${avg_order} | ${prev_avg} | ${avg_growth}% |

### 维度拆解

${dimension_breakdown}

### TOP 榜单

${top_ranking}

## 三、异常说明

${anomalies}

## 四、下周关注

${attention}

---
报告生成时间：${report_time}
数据周期：${date_range}
```

---

## 月报

```markdown
# ${business_line} 月报 ${date_range}

## 一、月度摘要

${summary}

## 二、指标趋势

| 指标 | 本月 | 上月 | 环比 | 去年同期 | 同比 |
|------|------|------|------|----------|------|
| 销售额 | ${total_sales} | ${prev_sales} | ${sales_growth}% | ${yoy_sales} | ${yoy_sales_growth}% |
| 订单量 | ${total_orders} | ${prev_orders} | ${order_growth}% | ${yoy_orders} | ${yoy_order_growth}% |
| 客单价 | ${avg_order} | ${prev_avg} | ${avg_growth}% | ${yoy_avg} | ${yoy_avg_growth}% |

### 趋势图

${trend_chart}

## 三、维度深度分析

### 渠道

| 渠道 | 销售额 | 占比 | 环比 |
|------|--------|------|------|
${channel_rows}

### 商品

#### 热销 TOP5
${top_products}

#### 滞销
${slow_moving}

## 四、用户分析

| 指标 | 数值 |
|------|------|
| 新增用户 | ${new_users} |
| 活跃用户 | ${active_users} |
| 复购率 | ${repurchase_rate}% |

### 留存

| 次日 | 7日 | 30日 |
|------|-----|------|
| ${d1}% | ${d7}% | ${d30}% |

## 五、异常检测

${anomalies}

## 六、下月展望

${attention}

---
报告生成时间：${report_time}
数据周期：${date_range}
```

---

## 对比报告

```markdown
# 对比分析报告：${dim_a} vs ${dim_b}

## 一、对比概览

| 指标 | ${dim_a} | ${dim_b} | 差异 | 变化率 |
|------|----------|----------|------|--------|
${comparison_rows}

## 二、差异指标明细

${difference_details}

## 三、可视化对比

${trend_chart}

## 四、差异原因分析

${insights}

## 五、结论与建议

${attention}

---
报告生成时间：${report_time}
对比维度：${dim_a} / ${dim_b}
数据周期：${date_range}
```

---

## 数据附件

**每个报告输出时必须附带数据文件。**

```
输出文件：
  {报告类型}_{日期}.md     ← 报告正文
  {报告类型}_{日期}.csv    ← 数据明细（报告内所有表格的源数据）

生成步骤：
  1. 按对应模板填充占位符，写入 .md 文件
  2. 调用 CSVConnector 将源数据写入同名 .csv
     - CSV 遵循 skills/visual/assets/export-template.md 格式规范
     - 编码 UTF-8，逗号分隔，LF 换行
  3. 两个文件放在同一输出目录
```

---

## 占位符速查

| 占位符 | 说明 | 格式 |
|--------|------|------|
| `${business_line}` | 业务线 | 文本 |
| `${date_range}` | 数据周期 | `YYYY-MM-DD`（日）、`YYYY年第N周`（周）、`YYYY年M月`（月） |
| `${report_time}` | 报告生成时间 | `YYYY-MM-DD HH:MM` |
| `${total_sales}` | 本期销售额 | 千分位分隔 |
| `${prev_sales}` | 上期销售额 | 千分位分隔 |
| `${sales_growth}` | 销售增长率 | `+12.5%` / `-3.2%` |
| `${total_orders}` | 本期订单量 | 千分位分隔 |
| `${prev_orders}` | 上期订单量 | 千分位分隔 |
| `${order_growth}` | 订单增长率 | `+8.3%` / `-1.5%` |
| `${avg_order}` | 本期客单价 | 保留 2 位小数 |
| `${prev_avg}` | 上期客单价 | 保留 2 位小数 |
| `${avg_growth}` | 客单价增长率 | `+5.0%` / `-2.1%` |
| `${new_users}` | 新增用户数 | 千分位分隔 |
| `${active_users}` | 活跃用户数 | 千分位分隔 |
| `${repurchase_rate}` | 复购率 | `25.0%` |
| `${d1}` `${d7}` `${d30}` | 留存率 | `45.2%` |
| `${yoy_sales}` | 去年同期销售额 | 千分位分隔 |
| `${yoy_sales_growth}` | 同比销售增长率 | `+15.0%` |
| `${summary}` | 摘要 | 一段话 |
| `${highlights}` | 亮点 | 要点列表 |
| `${anomalies}` | 异常 | 要点列表 |
| `${attention}` | 关注/建议 | 要点列表 |
| `${insights}` | 洞察/原因 | 要点列表 |
| `${channel_rows}` | 渠道表格行 | `| 渠道 | sales | pct | mom |` |
| `${top_products}` | 热销 TOP5 | Markdown 表格 |
| `${slow_moving}` | 滞销商品 | Markdown 表格 |
| `${top_ranking}` | TOP 榜单 | Markdown 表格 |
| `${comparison_rows}` | 对比表格行 | `| 指标 | A | B | diff | rate |` |
| `${dim_a}` `${dim_b}` | 对比维度 | 文本 |
| `${trend_chart}` | 趋势图 | `![标题](output/chart_xxx.png)` |
| `${current_sales}` `${current_time}` | 实时数据（仅日报） | — |
| `${sales_target}` `${target_rate}` | 目标/达成率（仅日报） | — |
