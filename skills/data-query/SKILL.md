---
name: data-query
description: 多数据源数据查询技能，支持自然语言转SQL、Hive、ClickHouse、Excel、CSV等数据源
---

# 数据查询技能 (Data Query)

## When to Activate

- Use this skill when querying data or retrieving data
- Use this skill when fetching data from databases or files
- Use this skill when working with Hive, ClickHouse, MySQL, Excel, or CSV
- Use this skill when running SQL queries
- Use this skill when performing parameter-based queries
- Use this skill when user speaks natural language like "查询上月销售额" or "看看本周转化率"

## 核心能力

1. **自然语言理解** ⭐ — 将用户自然语言转换为 SQL
2. **多数据源支持** — Hive、ClickHouse、MySQL、Excel、CSV
3. **SQL解析** — 支持标准SQL语法解析与优化
4. **参数化查询** — 支持时间范围、业务线等参数化条件
5. **结果统一化** — 输出CSV/Excel统一格式

## 输入参数

| 参数 | 说明 | 必填 | 示例 |
|------|------|------|------|
| query_input | 查询输入（自然语言或SQL） | 是 | "查询上月销售额" |
| data_source | 数据源类型 | 否 | hive/clickhouse/mysql/excel/csv |
| time_range | 时间范围 | 否 | 近7天/近30天/上月/自定义 |
| business_line | 业务线 | 否 | 电商/线下/团购 |
| fields | 需要的字段 | 否 | gmv, order_count, user_count |

## SQL安全规则（强制执行）

```
禁止操作:
- DROP / DELETE / TRUNCATE / ALTER
- 跨库查询（未授权）
- 敏感表（全表扫描无LIMIT）

限制:
- 单次查询返回上限: 10000行
- 单次查询超时: 30秒
```

## 执行指令

调用 `python scripts/execute_query.py` 执行数据查询，而非手动模拟数据读取：

```bash
# 文件数据源
python scripts/execute_query.py --source csv --path data/sample.csv
python scripts/execute_query.py --source json --path data/sample.json
python scripts/execute_query.py --source excel --path data/sample.xlsx --sheet Sheet1

# 数据库数据源 (需要真实连接配置)
python scripts/execute_query.py --source mysql --query "SELECT * FROM orders LIMIT 10" --host localhost --user root --database mydb

# 保存结果到文件
python scripts/execute_query.py --source csv --path data/sample.csv --output output/query_result.json
```

## 依赖

数据查询统一通过 `python scripts/execute_query.py` 执行。该脚本接口见 connectors/README.md。

管道的实际查询逻辑在 `scripts/ecommerce_pipeline.py` 的 step3 中实现，使用 csv.DictReader 读取本地 CSV 数据后由 industry-specific analyzer 处理。

### 指标口径参考

- 数据资产: data/indicator/core-indicator-dict.md（指标口径）
- 口径规则: rules/core/indicator-caliber.md

