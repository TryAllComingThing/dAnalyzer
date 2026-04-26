---
name: postgres-connector
description: PostgreSQL关系型数据库对接配置，支持JSON/JSONB类型和数组类型处理
type: datawarehouse
capabilities:
  - sql_query
  - data_export
  - json_query
  - array_processing
origin: ECC
---

# PostgreSQL对接配置

## 工具信息

- 名称：PostgreSQL
- 版本：14+
- 类型：关系型数据库

## 连接配置

- 连接地址：jdbc:postgresql://postgres-server:5432
- 数据库：业务数据库
- 认证方式：用户名+密码
- SSL：支持

## 支持操作

- SQL查询
- 数据导出
- JSON/JSONB类型
- 数组类型
- 存储过程

## 接口规范

### 查询接口

```sql
SELECT * FROM table_name LIMIT 100
```

- 超时时间：2分钟
- 最大返回行数：10000
- 支持JSON类型解析

### 导出接口

- 格式：CSV、JSON
- 压缩：GZIP

## 特殊功能

```sql
-- JSON字段提取
SELECT json_field->>'key' FROM table

-- 数组展开
SELECT unnest(array_column) FROM table
```

## 错误处理

- 连接失败：触发预警
- 查询超时：终止任务
- 语法错误：返回错误信息

## 输出格式

- 统一输出为CSV格式
- 字段分隔符：逗号
- 编码：UTF-8
