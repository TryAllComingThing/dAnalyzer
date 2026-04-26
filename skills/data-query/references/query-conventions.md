# 数据查询规范 (Data Query Conventions)

## 支持的数据源

| 数据源 | 优先级 | 连接方式 |
|--------|--------|----------|
| ClickHouse | P0 | JDBC/原生客户端 |
| Hive | P0 | JDBC/Thrift |
| MySQL | P1 | JDBC |
| PostgreSQL | P1 | JDBC |
| Excel | P2 | Pandas |
| CSV | P2 | Pandas |

## SQL 编写规范

### 1. 命名规范
- 表名: `database.schema.table` 全限定
- 字段名: 小写下划线
- 关键字: 大写

### 2. 查询优化
- 优先使用分区裁剪
- 避免 SELECT *
- 大表添加 LIMIT
- 复杂查询添加注释

### 3. 参数化查询
```sql
-- 使用变量占位
SELECT * FROM orders
WHERE dt = '{{date}}'
  AND status = '{{status}}'
```

## 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| 超时 | 增加超时参数，重试1次 |
| 权限不足 | 提示联系DBA |
| 语法错误 | 返回SQL供修正 |
| 空结果 | 提示检查过滤条件 |

## 输出格式

- 统一输出 CSV/JSON
- 自动添加元数据头（查询时间、数据量）
