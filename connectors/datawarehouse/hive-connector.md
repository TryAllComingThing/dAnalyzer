# Hive Connector

## 配置

| 字段 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| host | ✅ | localhost | HiveServer2 地址 |
| port | ❌ | 10000 | HiveServer2 端口 |
| database | ✅ | default | 数据库名 |
| user | ❌ | — | 用户名 |
| password | ❌ | — | 密码 |
| auth | ❌ | NONE | 认证机制 (NONE/NOSASL/KERBEROS) |

## 使用示例

```python
from connectors.datawarehouse.hive import HiveConnector

conn = HiveConnector({
    "host": "hive-prod.example.com",
    "port": "10000",
    "database": "dw",
    "user": "analyst",
})

result = conn.execute("SELECT region, SUM(gmv) FROM orders WHERE dt = '2026-04-28' GROUP BY region")
print(f"Rows: {result.row_count}, Time: {result.execution_time_ms}ms")
```

## 依赖

```bash
pip install pyhive  # 或: pip install impyla
```
