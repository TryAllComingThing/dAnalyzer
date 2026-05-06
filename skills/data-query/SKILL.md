---
name: data-query
description: Use when user needs to query data from registered sources (MySQL, ClickHouse, Hive, CSV, Excel, JSON) or describes data retrieval needs in natural language. Do NOT use for data write/delete operations or unregistered data sources.
---

# 数据查询技能 (Data Query)

## 概述

多数据源统一查询入口，支持自然语言转 SQL 与结构化查询两种模式。覆盖数据库（MySQL/ClickHouse/Hive）和文件（CSV/Excel/JSON/TSV），通过 `execute_query.py` 统一接口执行，自动校验 SQL 安全性，返回标准化 JSON 结果供下游技能消费。

## 何时使用

- **触发:** 用户需要从任一注册数据源取数、执行 SQL 查询或用自然语言描述取数需求
- **触发:** 操作 MySQL、ClickHouse、Hive、CSV、Excel、JSON 或 TSV 文件
- **触发:** 执行含时间范围或业务筛选的参数化查询
- **不要用于:** 数据写入、删除或修改操作（本技能只读）
- **不要用于:** 未经 `datasources.yaml` 注册的数据源（先触发 danalyzer-core 数据匹配步骤）

---

## 核心步骤

1. **获取 Schema** — `python3 dAnalyzer/scripts/execute_query.py --datasource <name> --schema`，获取表结构/字段/类型 → 详见「执行指令」
2. **判定数据源类型** — schema 返回的 `type` 字段为 `database` 或 `file`
3. **Database 路径** — 基于 schema 真实表名列名生成 SQL → 校验（静态检查+EXPLAIN）→ 校验失败则查错误表重生成（最多 3 次）→ 执行并返回 → 详见「数据获取执行流程」和「SQL校验错误处理」
4. **File 路径** — 直接读取全量数据 → 在 Python 中对 rows 进行过滤/聚合/排序/分组操作 → 详见「数据获取执行流程 > File 路径」
5. **输出标准化** — 统一 `{"columns": [...], "rows": [[...], ...], "row_count": N, "source": "<name>"}` 格式传递下游

---

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

> 对应核心步骤第 3-4 步

所有查询必须先通过 `--schema` 确定数据源类型，再按对应路径执行。不可跳过。

### 第 1 步: 获取 schema + 判定类型

```bash
python3 dAnalyzer/scripts/execute_query.py --datasource <name> --schema
```
→ 返回 JSON，其中 `"type"` 字段为 `"database"` 或 `"file"`。禁止凭记忆猜测表名/列名/路径。

### 第 2 步: 按类型分支执行

**type = "database":**

| 子步骤 | 操作 | 说明 |
|--------|------|------|
| 2a. 生成 SQL | 基于 schema 返回的 `tables[].columns` 生成 SELECT | 表名和列名必须来自 schema，不得编造 |
| 2b. 校验 SQL | `python3 dAnalyzer/scripts/execute_query.py --datasource <name> --query "<SQL>"` | 自动执行 静态检查→EXPLAIN |
| 2c. 校验失败 → 重生成 | 根据 error_type 查错误处理表，最多重试 3 次 | 仍失败则终止并报告 |
| 2d. 校验通过 → 返回 | 结果含 columns/rows/row_count | — |

**type = "file":**

| 子步骤 | 操作 | 说明 |
|--------|------|------|
| 2a. 读取文件 | `python3 dAnalyzer/scripts/execute_query.py --datasource <name>` | 返回全量数据 (columns + rows) |
| 2b. Python 分析 | 对 rows 进行过滤/聚合/排序/分组 | rows 为 `list[dict]`，值均为字符串，数值操作需 float/int 转换 |

### 第 3 步: 输出标准化

统一 JSON 格式传递给后续技能：
```json
{"columns": [...], "rows": [[...], ...], "row_count": N, "source": "<datasource_name>"}
```

## SQL 校验错误处理

> 对应 核心步骤 第 3 步

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

> 对应 核心步骤 第 1 步

调用 `python3 dAnalyzer/scripts/execute_query.py` 执行数据查询，而非手动模拟数据读取。

### 推荐方式：按数据源名称

```bash
# 获取数据源的表结构信息
python3 dAnalyzer/scripts/execute_query.py --datasource fmcg_orders --schema

# 数据库查询
python3 dAnalyzer/scripts/execute_query.py --datasource fmcg_orders --query "SELECT category, SUM(actual_amount) FROM orders WHERE order_date > '2024-01-01' GROUP BY category"

# 文件数据源
python3 dAnalyzer/scripts/execute_query.py --datasource test_orders
python3 dAnalyzer/scripts/execute_query.py --datasource test_sales
```

### 向后兼容：直接指定连接参数

```bash
# 文件数据源
python3 dAnalyzer/scripts/execute_query.py --source csv --path knowledge/sample.csv
python3 dAnalyzer/scripts/execute_query.py --source json --path knowledge/sample.json
python3 dAnalyzer/scripts/execute_query.py --source excel --path knowledge/sample.xlsx --sheet Sheet1

# 数据库数据源 (需要真实连接配置)
python3 dAnalyzer/scripts/execute_query.py --source mysql --query "SELECT * FROM orders LIMIT 10" --host localhost --user root --database mydb
```

### 仅校验不执行

```bash
python3 dAnalyzer/scripts/execute_query.py --source mysql --query "<SQL>" --validate-only
```

### 保存结果

```bash
python3 dAnalyzer/scripts/execute_query.py --datasource fmcg_orders --query "..." --output output/query_result.json
```

## 依赖

数据查询统一通过 `python3 dAnalyzer/scripts/execute_query.py` 执行。该脚本接口见 connectors/README.md。

管道的实际查询逻辑在 `scripts/ecommerce_pipeline.py` 的 step3 中实现，使用 csv.DictReader 读取本地 CSV 数据后由 industry-specific analyzer 处理。

### 子技能参考文件

| 文件 | 用途 |
|------|------|
| `references/common-sql-template.md` | 通用 SQL 查询模板（SELECT/JOIN/GROUP BY） |
| `references/funnel-sql-template.md` | 漏斗分析 SQL 模板 |
| `references/time-analysis-template.md` | 时间序列分析 SQL 模板 |
| `references/user-analysis-template.md` | 用户分析 SQL 模板 |
| `references/query-conventions.md` | 查询规范与命名约定 |

---

## 常见借口与纠正

| 借口 | 现实 |
|--------|---------|
| "我记得这个表的列名，直接写 SQL" | 凭记忆写 SQL 是查询失败的第一大原因；始终先 `--schema` |
| "CSV 文件不大，我手动解析" | 绕过 `execute_query.py` 会丢失 schema 校验、错误处理和标准化输出 |
| "这个 SQL 很简单不需要校验" | 即使是简单 SELECT，表名/列名拼写错误也会在执行时才暴露 |

## 红线

- **检测到写操作:** SQL 包含 DROP、DELETE、TRUNCATE 或 ALTER — 立即拒绝
- **大表无 LIMIT:** 查询无 LIMIT 且表超 10,000 行 — 执行前强制加 LIMIT
- **Schema 不匹配:** `--schema` 返回的表/列与用户意图不符 — 先确认再猜测映射
- **连续 3 次校验失败:** SQL 校验连续失败 3 次 — 中止并报告，不无限重试

## 验证

1. 验证 schema 已获取：确认每次查询前 `--schema` 已运行且返回有效表/列数据
2. 验证 SQL 只读：确认无写操作关键字（DROP/DELETE/TRUNCATE/ALTER）
3. 验证 EXPLAIN 通过：确认数据库查询已完成校验无错误
4. 验证行数限制：确认返回行数不超过 10,000
5. 验证输出格式：确认结果匹配 `{columns, rows, row_count, source}` 格式


