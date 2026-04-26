---
name: query sql
description: 直接执行 SQL 查询，返回查询结果
trigger: query sql
related_skills:
  - data-query
  - security
---

# /query sql - SQL 直接查询

## 功能说明

直接执行 SQL 语句进行数据查询，支持多种数据源。

## 使用方式

```
/query sql <SQL语句>
```

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| SQL语句 | 是 | 完整的 SELECT 语句 |

## 数据源支持

| 前缀 | 数据源 | 示例 |
|------|--------|------|
| hive: | Hive 数据仓库 | `hive: SELECT * FROM sales` |
| mysql: | MySQL 数据库 | `mysql: SELECT * FROM orders` |
| csv: | CSV 文件 | `csv: /data/sales.csv` |
| excel: | Excel 文件 | `excel: /data/sales.xlsx` |
| 默认 | 智能选择 | 系统自动判断 |

## 使用示例

```bash
# 查询 Hive 数据
/query sql SELECT date, SUM(amount) as revenue FROM sales GROUP BY date

# 查询 MySQL
/query sql mysql: SELECT * FROM orders WHERE created_at > '2026-04-01'

# 查询 CSV
/query sql csv:/data/orders.csv SELECT * WHERE amount > 1000

# 带条件查询
/query sql SELECT region, COUNT(*) as cnt FROM sales GROUP BY region ORDER BY cnt DESC
```

## 输出格式

```json
{
  "success": true,
  "data_source": "hive:sales",
  "row_count": 100,
  "columns": ["date", "revenue"],
  "data": [
    {"date": "2026-04-01", "revenue": 50000},
    {"date": "2026-04-02", "revenue": 48000}
  ]
}
```

## 自动处理

- ✅ 安全检查 (脱敏 + 合规)
- ✅ 结果格式化
- ✅ 分页处理 (大结果集)

## 注意事项

1. **SQL 语法**: 确保语法正确，系统不做语法校验
2. **权限**: 需有对应数据源的查询权限
3. **结果量**: 建议使用 LIMIT 限制结果数量
4. **敏感数据**: 系统会自动脱敏处理

## 相关命令

- `/query nl` - 自然语言查询
- `/query export` - 数据导出
- `/help query` - 返回查询命令列表
