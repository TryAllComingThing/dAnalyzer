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
2. **SQL 校验与重生成** — 生成 SQL 后先验证再执行，失败则基于 schema_hint 重生成
3. **多数据源支持** — Hive、ClickHouse、MySQL、Excel、CSV
4. **SQL解析** — 支持标准SQL语法解析与优化
5. **参数化查询** — 支持时间范围、业务线等参数化条件
6. **结果统一化** — 输出CSV/Excel统一格式

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

## 数据获取执行流程（强制）

所有查询必须先通过 `--schema` 确定数据源类型，再按对应路径执行。不可跳过。

```
1. 获取 schema + 判定类型
   python scripts/execute_query.py --datasource <name> --schema
   → 返回 JSON，其中 "type" 字段为 "database" 或 "file"。
   → 禁止凭记忆猜测表名/列名/路径。

2. 分支：按 type 执行不同路径 ──────────────────────┐
                                                      │
   ┌─ type = "database" ───────────────────────────┐  │
   │                                                │  │
   │  2a. 生成 SQL                                  │  │
   │      基于 schema 返回的 tables[].columns 生成   │  │
   │      SELECT 语句。表名和列名必须来自 schema，   │  │
   │      不得编造。                                 │  │
   │                                                │  │
   │  2b. 校验 SQL                                  │  │
   │      python scripts/execute_query.py \         │  │
   │        --datasource <name> --query "<SQL>"     │  │
   │      execute_query 自动执行 静态检查→EXPLAIN。 │  │
   │                                                │  │
   │  2c. 校验失败 → 重生成                         │  │
   │      根据返回的 error_type 查表处理。           │  │
   │      最多重试 3 次，仍失败则终止并报告。        │  │
   │                                                │  │
   │  2d. 校验通过 → 返回数据                       │  │
   │      结果已包含 columns/rows/row_count。        │  │
   │                                                │  │
   └────────────────────────────────────────────────┘  │
                                                      │
   ┌─ type = "file" ───────────────────────────────┐  │
   │                                                │  │
   │  2a. 读取文件 (无需 SQL)                       │  │
   │      python scripts/execute_query.py \         │  │
   │        --datasource <name>                     │  │
   │      → 返回全量数据 (columns + rows)。         │  │
   │                                                │  │
   │  2b. 用 Python 分析数据                        │  │
   │      文件数据不支持 SQL，过滤/聚合/排序等操作   │  │
   │      在 Python 中对返回的 rows 进行。          │  │
   │      rows 是 list[dict]，值均为字符串，        │  │
   │      数值操作需要 float/int 转换。             │  │
   │      - 过滤: [r for r in rows                  │  │
   │               if float(r['amount']) > 100]     │  │
   │      - 聚合: sum(float(r['amount'])            │  │
   │               for r in rows)                   │  │
   │      - 排序: sorted(rows,                      │  │
   │               key=lambda r: float(r['amount']))│  │
   │      - 分组: 用 dict 按 r['category'] 归类     │  │
   │      - 计数: len(rows) 或 Counter              │  │
   │                                                │  │
   └────────────────────────────────────────────────┘  │
                                                      │
3. 数据传递给后续技能 (data-clean / data-analysis 等)  │
   → 统一 JSON 格式:                                 │
   → {"columns": [...], "rows": [[...], ...],         │
   →  "row_count": N, "source": "<datasource_name>"}  │
```

## SQL 校验错误处理

| error_type | 含义 | 处理 |
|-----------|------|------|
| `SQL_EMPTY` | 空语句 | 检查是否有用户查询条件未转换为 SQL |
| `SQL_NOT_SELECT` | 非 SELECT 语句 | 改为只读查询，移除写操作 |
| `SQL_FORBIDDEN` | 包含写操作关键字 | **立即中止**，向用户说明不允许写操作 |
| `SQL_SYNTAX_ERROR` | 语法错误 | 检查关键字拼写、逗号位置、括号配对，重新生成 |
| `SQL_TABLE_NOT_FOUND` | 表不存在 | 用 `--schema` 获取真实表名，重新生成 |
| `SQL_COLUMN_NOT_FOUND` | 列不存在 | 用 `--schema` 获取真实列名，重新生成 |
| `CONNECTION_CONFIG_ERROR` | 连接配置不完整 | 用 `--datasource <name>` 指定已注册数据源 |
| `CONNECTION_ERROR` | 数据库不可达 | 重试 1 次，仍失败则告知用户连接问题 |
| `SQL_EXECUTION_ERROR` | 运行时错误 | 检查查询逻辑（如 GROUP BY 与 SELECT 不一致），重新生成 |

## 执行指令

调用 `python scripts/execute_query.py` 执行数据查询，而非手动模拟数据读取。

### 推荐方式：按数据源名称

```bash
# 获取数据源的表结构信息
python scripts/execute_query.py --datasource fmcg_orders --schema

# 数据库查询
python scripts/execute_query.py --datasource fmcg_orders --query "SELECT category, SUM(actual_amount) FROM orders WHERE order_date > '2024-01-01' GROUP BY category"

# 文件数据源
python scripts/execute_query.py --datasource test_orders
python scripts/execute_query.py --datasource test_sales
```

### 向后兼容：直接指定连接参数

```bash
# 文件数据源
python scripts/execute_query.py --source csv --path knowledge/sample.csv
python scripts/execute_query.py --source json --path knowledge/sample.json
python scripts/execute_query.py --source excel --path knowledge/sample.xlsx --sheet Sheet1

# 数据库数据源 (需要真实连接配置)
python scripts/execute_query.py --source mysql --query "SELECT * FROM orders LIMIT 10" --host localhost --user root --database mydb
```

### 仅校验不执行

```bash
python scripts/execute_query.py --source mysql --query "<SQL>" --validate-only
```

### 保存结果

```bash
python scripts/execute_query.py --datasource fmcg_orders --query "..." --output output/query_result.json
```

## 依赖

数据查询统一通过 `python scripts/execute_query.py` 执行。该脚本接口见 connectors/README.md。

管道的实际查询逻辑在 `scripts/ecommerce_pipeline.py` 的 step3 中实现，使用 csv.DictReader 读取本地 CSV 数据后由 industry-specific analyzer 处理。


