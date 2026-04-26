# dAnalyzer 命令中心

> 多层帮助系统 + 分域命令管理

---

## 使用方式

```
/dhelp                   → 显示所有命令分类
/dhelp query             → 显示查询域命令
/dhelp query nl          → 显示自然语言查询详细用法
/dhelp analysis          → 显示分析域命令
/dhelp report            → 显示报告域命令
```

---

## 命令分类

### 📊 查询命令 (query)

| 命令 | 说明 | 示例 |
|------|------|------|
| `/query sql` | SQL直接查询 | `/query sql SELECT * FROM sales` |
| `/query nl` | 自然语言查询 | `/query nl 本月销售额` |
| `/query export` | 数据导出 | `/query export csv sales_2026` |

**详细文档**: [query/](query/)

### 📈 分析命令 (analysis)

| 命令 | 说明 | 示例 |
|------|------|------|
| `/analysis trend` | 趋势分析 | `/analysis trend 销售趋势` |
| `/analysis rfm` | RFM用户分析 | `/analysis rfm user_behavior` |
| `/analysis funnel` | 漏斗分析 | `/analysis funnel 注册-购买` |
| `/analysis audit` | 审计分析 | `/analysis audit --time=7d` |

**详细文档**: [analysis/](analysis/)

### 📄 报告命令 (report)

| 命令 | 说明 | 示例 |
|------|------|------|
| `/report daily` | 日报生成 | `/report daily sales` |
| `/report weekly` | 周报生成 | `/report weekly sales` |
| `/report custom` | 自定义报告 | `/report custom name:xxx` |

**详细文档**: [report/](report/)

---

## 常用场景

| 场景 | 推荐命令 |
|------|----------|
| 快速查询数据 | `/query nl 本月销售` |
| SQL 直接查询 | `/query sql SELECT * FROM sales` |
| 生成图表 | `/analysis trend 销售` |
| 用户分析 | `/analysis rfm user_orders` |
| 转化分析 | `/analysis funnel 注册-购买` |
| 生成日报 | `/report daily sales` |
| 生成周报 | `/report weekly sales` |

---

## 文件统计

- **目录**: commands/
- **分类**: 3个 (query/analysis/report)
- **命令**: 10个
- **帮助**: /dhelp 多层支持
