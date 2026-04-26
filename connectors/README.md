# 第三方工具对接适配层 (connectors)

## 目录用途

第三方工具对接适配层，打通外部工具与数分ECC的连接。主要包括：

- **数仓对接（datawarehouse）**：Hive、ClickHouse、MySQL等主流数仓接口
- **辅助工具对接（tool）**：Excel、Python、CSV、JSON等文件处理

## 文件格式规范

每个connector文件必须包含YAML frontmatter：

```yaml
---
name: connector-name
description: 连接器描述，说明支持的功能
type: datawarehouse|tool
capabilities:
  - capability_1
  - capability_2
origin: ECC
---
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| name | 是 | 连接器名称，使用kebab-case格式 |
| description | 是 | 连接器功能描述 |
| type | 是 | 类型：datawarehouse/tool |
| capabilities | 是 | 支持的功能列表 |
| origin | 是 | 来源：ECC |

## 目录结构

```
connectors/
├── datawarehouse/       # 数仓对接 (5个)
│   ├── __init__.py
│   ├── base.py          # BaseConnector基类
│   ├── mysql.py         # MySQL连接器
│   ├── clickhouse.py    # ClickHouse连接器
│   ├── hive.py          # Hive连接器
│   ├── postgres.py      # PostgreSQL连接器
│   ├── oracle.py        # Oracle连接器
│   ├── requirements.txt # 依赖声明
│   └── *-connector.md   # 文档(5个)
└── tool/                # 工具对接 (4个)
    ├── __init__.py
    ├── base.py          # BaseFileConnector基类
    ├── csv_connector.py # CSV处理
    ├── json_connector.py# JSON处理
    ├── excel_connector.py# Excel处理
    ├── python_connector.py# Python脚本执行
    ├── requirements.txt # 依赖声明
    └── *-connector.md   # 文档(4个)
```

## 连接器列表 (9个)

### datawarehouse (数仓对接) - 5个
| 连接器 | 说明 | Python模块 |
|--------|------|-----------|
| mysql-connector | MySQL对接 | mysql.py |
| clickhouse-connector | ClickHouse对接 | clickhouse.py |
| hive-connector | Hive数仓对接 | hive.py |
| postgres-connector | PostgreSQL对接 | postgres.py |
| oracle-connector | Oracle对接 | oracle.py |

### tool (工具对接) - 4个
| 连接器 | 说明 | Python模块 |
|--------|------|-----------|
| csv-connector | CSV对接 | csv_connector.py |
| json-connector | JSON对接 | json_connector.py |
| excel-connector | Excel对接 | excel_connector.py |
| python-connector | Python脚本执行 | python_connector.py |

## 使用指南

### 数据仓库连接

```python
from connectors.datawarehouse import MySQLConnector, ClickHouseConnector

# 方式1: 传入配置
config = {
    "host": "localhost",
    "port": "3306",
    "database": "sales",
    "user": "root",
    "password": "pass"
}
with MySQLConnector(config) as conn:
    result = conn.execute("SELECT * FROM orders LIMIT 100")
    result.to_csv("output.csv")

# 方式2: 使用环境变量 (MYSQL_HOST, MYSQL_USER, ...)
conn = MySQLConnector({"database": "sales"})
result = conn.execute("SELECT * FROM orders")
```

### 文件工具

```python
from connectors.tool import CSVConnector, JSONConnector, ExcelConnector

# CSV处理
csv = CSVConnector()
result = csv.read("data.csv", delimiter=",", encoding="utf-8")
csv.write(records, "output.csv")

# JSON处理
json_conn = JSONConnector()
result = json_conn.read("data.json")
json_conn.write(records, "output.json")

# Excel处理
excel = ExcelConnector()
result = excel.read("data.xlsx")
excel.write(records, "output.xlsx")
```

## 依赖安装

```bash
# 数据仓库依赖
pip install -r connectors/datawarehouse/requirements.txt

# 文件工具依赖
pip install -r connectors/tool/requirements.txt
```

## 使用场景

| 场景 | 使用的Connector |
|------|-----------------|
| MySQL取数 | datawarehouse/mysql-connector |
| ClickHouse分析 | datawarehouse/clickhouse-connector |
| Hive大数据查询 | datawarehouse/hive-connector |
| PostgreSQL取数 | datawarehouse/postgres-connector |
| Oracle取数 | datawarehouse/oracle-connector |
| CSV导出/读取 | tool/csv-connector |
| JSON导出/读取 | tool/json-connector |
| Excel导出/读取 | tool/excel-connector |
| Python脚本执行 | tool/python-connector |

## 调用流程

```
1. Agent/Skill 调用 connector
   ↓
2. 读取 connector 配置（包含frontmatter）
   ↓
3. 根据 capabilities 执行对应操作
   ↓
4. 返回标准化结果（CSV/DataFrame）
```

## 依赖关系

```
datawarehouse (取数)
    ↓
data-clean (清洗) → data-quality-check (校验)
    ↓
desensitization (脱敏) → compliance-check (合规)
    ↓
tool (导出)
    ↓
log (归档)
```

## 配置规范

连接配置中的敏感信息应使用环境变量：

```markdown
- 连接地址：${MYSQL_HOST:localhost}
- 用户名：${MYSQL_USER:root}
- 密码：${MYSQL_PASSWORD:}
```

## 文件统计

- datawarehouse: 5个MD + 6个Python文件 + 1个requirements.txt
- tool: 4个MD + 5个Python文件 + 1个requirements.txt
- **总计: 9个MD + 11个Python + 2个requirements.txt = 22文件**

## 注意事项

1. 连接器配置中的认证信息不应硬编码，应使用环境变量
2. 对接失败需触发预警并记录日志
3. 工具输出需统一格式（CSV/Excel）
4. 定期检查连接器配置的有效性
5. 所有connector均提供Python实现，可直接导入使用
