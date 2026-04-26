---
name: clickhouse-connector
description: ClickHouse OLAP数据库对接配置，支持SQL查询、数据导出和特殊语法
type: datawarehouse
capabilities:
  - sql_query
  - data_export
  - metadata_query
  - partition_pruning
  - sampling_query
origin: ECC
---

# ClickHouse对接配置

## 工具信息

- 名称：ClickHouse
- 版本：23.x
- 类型：OLAP数据库

## 连接配置

- 连接地址：jdbc:clickhouse://clickhouse-server:8123
- 数据库：default
- 认证方式：用户名+密码
- 只读权限：是

## 支持操作

- SQL查询
- 数据导出
- 表结构查询
- 分区信息查询

## 接口规范

### 查询接口

```sql
SELECT * FROM table_name LIMIT 100
```

- 超时时间：5分钟
- 最大返回行数：10000
- 支持物化视图查询

### 导出接口

- 格式：CSV、JSON、Parquet
- 压缩：LZ4、ZSTD

### 特殊语法

```sql
-- 分区裁剪
SELECT * FROM table WHERE partition='202604'

-- 采样查询
SELECT * FROM table SAMPLE 0.1

-- 物化列
SELECT uniqExact(user_id) FROM table
```

## 错误处理

- 连接失败：触发预警，等待重试
- 查询超时：终止任务，记录日志
- 语法错误：返回错误信息

## 输出格式

- 统一输出为CSV格式
- 字段分隔符：逗号
- 编码：UTF-8
- 日期格式：YYYY-MM-DD
- 时间格式：YYYY-MM-DD HH:MM:SS
