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

### 方式1: 自然语言输入（业务人员使用）
```
用户输入示例：
- "查询上月销售额"
- "看看本周的转化率"
- "帮我查查各地区的用户活跃情况"
- "分析下新用户的留存"
```

### 方式2: SQL输入（技术人员使用）
```
用户输入示例：
- SELECT * FROM sales WHERE date >= '2026-01-01'
- 查询2026年4月的数据
```

| 参数 | 说明 | 必填 | 示例 |
|------|------|------|------|
| query_input | 查询输入（自然语言或SQL） | 是 | "查询上月销售额" |
| data_source | 数据源类型 | 否 | hive/clickhouse/mysql/excel/csv |
| time_range | 时间范围 | 否 | 近7天/近30天/上月/自定义 |
| business_line | 业务线 | 否 | 电商/线下/团购 |
| fields | 需要的字段 | 否 | gmv, order_count, user_count |

## 执行流程

```
┌─────────────────────────────────────────────────────────────┐
│                    data-query 技能                          │
├─────────────────────────────────────────────────────────────┤
│  输入：query_input（自然语言 OR SQL）                        │
│                     │                                       │
│                     ▼                                       │
│         ┌─────────────────────┐                            │
│         │ 判断输入类型         │                            │
│         └──────────┬──────────┘                            │
│                    │                                        │
│        ┌───────────┴───────────┐                           │
│        │                         │                           │
│        ▼                         ▼                           │
│   自然语言输入？             SQL直接输入？                    │
│        │                         │                           │
│        ▼                         ▼                           │
│   ┌─────────────┐         ┌─────────────┐                  │
│   │  1.NL2SQL   │         │  SQL校验    │                  │
│   │  生成SQL    │         │  (安全检查) │                  │
│   └──────┬──────┘         └──────┬──────┘                  │
│          │                        │                          │
│          ▼                        ▼                          │
│   ┌─────────────┐         ┌─────────────┐                  │
│   │ 2.表结构    │         │ 3.执行SQL  │                  │
│   │ 理解        │────────▶│ (调用连接器) │                  │
│   └──────┬──────┘         └──────┬──────┘                  │
│          │                        │                          │
│          └───────────┬───────────┘                          │
│                      ▼                                      │
│              ┌─────────────┐                                 │
│              │ 4.结果转换  │                                 │
│              │ (统一格式)   │                                 │
│              └──────┬──────┘                                 │
│                     ▼                                        │
│              ┌─────────────┐                                 │
│              │ 输出结果     │                                 │
│              └─────────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: NL2SQL 转换（自然语言输入时）

```
输入: "查询上月各产品销售额"

处理流程:
1. 实体识别
   - 时间: 上月 → 2026-03-01 ~ 2026-03-31
   - 指标: 销售额 → gmv / revenue
   - 维度: 产品 → product_name / product_id

2. 表结构理解
   - 查找相关表: sales, order, product
   - 识别字段: sale_amount, product_name, sale_date
   - 理解表关系: order → order_item → product

3. SQL生成
   SELECT product_name, SUM(sale_amount) as sales
   FROM sales
   WHERE sale_date >= '2026-03-01' AND sale_date <= '2026-03-31'
   GROUP BY product_name
   ORDER BY sales DESC
```

### Step 2: SQL安全校验（必执行）

```
禁止操作:
- DROP / DELETE / TRUNCATE / ALTER
- 跨库查询（未授权）
- 敏感表（全表扫描无LIMIT）

限制:
- 单次查询返回上限: 10000行
- 单次查询超时: 30秒
```

### Step 3: 执行SQL / 读取数据

**⚠️ 强制使用 Connector，禁止用标准库裸读**。

```
MUST:  from connectors.tool.csv_connector import CSVConnector
MUST:  from connectors.tool.json_connector import JSONConnector
MUST:  from connectors.tool.excel_connector import ExcelConnector
NEVER: import csv / json.load / open() 裸读数据文件
```

#### CSV 数据源

```python
import sys; sys.path.insert(0, '.')
from connectors.tool.csv_connector import CSVConnector

c = CSVConnector()
result = c.read('data/file.csv')
# result.row_count, result.columns 可用
```

#### JSON 数据源

```python
from connectors.tool.json_connector import JSONConnector

c = JSONConnector()
result = c.read('data/file.json')
data = result.raw_data  # list[dict]
```

#### Excel 数据源

```python
from connectors.tool.excel_connector import ExcelConnector

c = ExcelConnector()
result = c.read('data/file.xlsx')
# result.raw_data 可用
```

#### 数据库数据源 (MySQL/ClickHouse/Hive/PG/Oracle)

```python
# MySQL
from connectors.datawarehouse.mysql import MySQLConnector
conn = MySQLConnector({"host": "...", "database": "...", "user": "...", "password": "..."})
result = conn.execute("SELECT ...")

# ClickHouse
from connectors.datawarehouse.clickhouse import ClickHouseConnector
conn = ClickHouseConnector({"host": "...", "database": "..."})
result = conn.execute("SELECT ...")
```

**违规检测**:
- [ ] 是否用了 `import csv` 而不是 `CSVConnector`？
- [ ] 是否用了 `json.load(open(...))` 而不是 `JSONConnector`？
- [ ] 是否用了 `open().read()` 手动解析而不是用 Connector？

### Step 4: 结果转换

```
输出统一格式:
- 字段说明 (field_description)
- 数据行数 (row_count)
- 数据样例 (sample_data)
- 数据文件 (csv/excel)
```

## 输出结果

```json
{
  "status": "success",
  "data": {
    "sql_generated": "SELECT ...",  // NL2SQL时输出
    "query_sql": "SELECT ...",       // 实际执行的SQL
    "field_description": [...],
    "row_count": 1000,
    "sample_data": [...],
    "data_file": "output/query_result.csv"
  },
  "metadata": {
    "data_source": "hive",
    "query_time": "2026-04-25 10:30:00",
    "duration_ms": 1200
  }
}
```

## NL2SQL 提示词模板

```
你是SQL生成专家。根据用户需求生成查询SQL。

用户需求: {user_query}
数据库表结构:
{tables_schema}

要求:
1. 生成的SQL要兼容Hive/ClickHouse语法
2. 只生成SELECT查询，禁止其他操作
3. 添加合理的WHERE条件
4. 如有时间字段，使用日期函数处理
5. 如有聚合需求，使用GROUP BY

请直接输出SQL语句，不要其他解释。
```

## 依赖配置

### Connector 模块（强制使用）

| 数据源 | 导入路径 | 模块文件 |
|--------|---------|----------|
| CSV | `from connectors.tool.csv_connector import CSVConnector` | connectors/tool/csv_connector.py |
| JSON | `from connectors.tool.json_connector import JSONConnector` | connectors/tool/json_connector.py |
| Excel | `from connectors.tool.excel_connector import ExcelConnector` | connectors/tool/excel_connector.py |
| MySQL | `from connectors.datawarehouse.mysql import MySQLConnector` | connectors/datawarehouse/mysql.py |
| ClickHouse | `from connectors.datawarehouse.clickhouse import ClickHouseConnector` | connectors/datawarehouse/clickhouse.py |
| Hive | `from connectors.datawarehouse.hive import HiveConnector` | connectors/datawarehouse/hive.py |
| PG | `from connectors.datawarehouse.postgres import PostgresConnector` | connectors/datawarehouse/postgres.py |

### 其他依赖

- 数据资产: data/indicator/core-indicator-dict.md（指标口径）
- 口径规则: rules/core/indicator-caliber.md

## 使用示例

### 示例1: 自然语言查询（业务人员）
```
用户: 帮我看看上个月各地区的销售额

输入:
{
  "query_input": "上个月各地区销售额",
  "data_source": "hive",
  "time_range": "上月"
}

处理:
1. NL2SQL → SELECT region, SUM(sale_amount) FROM sales WHERE ...
2. 执行SQL
3. 返回结果

输出:
- SQL: SELECT region, SUM(sale_amount) as sales FROM sales ...
- 数据: [{region: "华东", sales: 100000}, {region: "华北", sales: 80000}, ...]
```

### 示例2: SQL直接查询（技术人员）
```
用户: SELECT product_name, COUNT(*) FROM orders WHERE created_at >= '2026-04-01' GROUP BY product_name

输入:
{
  "query_input": "SELECT product_name, COUNT(*) FROM orders WHERE created_at >= '2026-04-01' GROUP BY product_name",
  "data_source": "hive"
}

处理:
1. SQL安全校验
2. 执行SQL
3. 返回结果
```

### 示例3: 参数化查询
```
用户: 查询本周转化率

输入:
{
  "query_input": "本周转化率",
  "data_source": "hive",
  "time_range": "本周",
  "business_line": "电商"
}
```
