---
name: dhelp
description: dAnalyzer 多层帮助系统，显示所有可用命令及使用方法
trigger: dhelp
---

# dAnalyzer 命令帮助系统

## 使用方式

```
/dhelp                   → 显示所有命令分类
/dhelp query             → 显示查询域命令
/dhelp analysis          → 显示分析域命令
/dhelp report            → 显示报告域命令
/dhelp <具体命令>        → 显示命令详细用法
```

---

## 命令分类

### 📊 查询命令 (query)

| 命令 | 说明 | 示例 |
|------|------|------|
| `/query sql` | SQL直接查询 | `/query sql SELECT * FROM sales` |
| `/query nl` | 自然语言查询 | `/query nl 本月销售额` |
| `/query export` | 数据导出 | `/query export csv sales_2026` |

### 📈 分析命令 (analysis)

| 命令 | 说明 | 示例 |
|------|------|------|
| `/analysis trend` | 趋势分析 | `/analysis trend 销售趋势` |
| `/analysis rfm` | RFM用户分析 | `/analysis rfm user_behavior` |
| `/analysis funnel` | 漏斗分析 | `/analysis funnel 注册-购买` |
| `/analysis audit` | 审计分析 | `/analysis audit 2026-04` |

### 📄 报告命令 (report)

| 命令 | 说明 | 示例 |
|------|------|------|
| `/report daily` | 日报生成 | `/report daily sales` |
| `/report weekly` | 周报生成 | `/report weekly sales` |
| `/report custom` | 自定义报告 | `/report custom 月度分析` |

---

## 快速开始

### 1. 数据查询

```bash
# SQL 查询
/query sql SELECT date, SUM(amount) FROM orders GROUP BY date

# 自然语言查询
/query nl 本月销售额最高的产品是什么

# 导出数据
/query export csv orders_2026
```

### 2. 数据分析

```bash
# 趋势分析
/analysis trend 销售趋势

# RFM 用户分析
/analysis rfm user_behavior

# 漏斗分析
/analysis funnel 注册-登录-下单-支付
```

### 3. 生成报告

```bash
# 日报
/report daily sales

# 周报
/report weekly sales

# 自定义报告
/report custom 月度运营报告
```

---

## 多层帮助

### 查看分类帮助

```bash
/dhelp query          # 查看所有查询命令
/dhelp analysis       # 查看所有分析命令
/dhelp report         # 查看所有报告命令
```

### 查看命令详情

```bash
/dhelp query sql      # 查看 SQL 查询详细用法
/dhelp query nl       # 查看自然语言查询详细用法
/dhelp analysis rfm  # 查看 RFM 分析详细用法
```

---

## 常用场景

| 场景 | 推荐命令 |
|------|----------|
| 快速查询数据 | `/query nl 本月销售` |
| 生成图表 | `/query nl 销售趋势图` |
| 用户分析 | `/analysis rfm 用户表` |
| 转化分析 | `/analysis funnel 购买漏斗` |
| 生成周报 | `/report weekly 运营` |

---

## 系统信息

- **版本**: 3.5
- **行业**: 支持电商、物流、制造、金融
- **数据源**: 支持 CSV、Excel、数据库
