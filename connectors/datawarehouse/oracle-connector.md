---
name: oracle-connector
description: Oracle Database对接配置，支持SQL查询、数据导出和存储过程调用
type: datawarehouse
capabilities:
  - sql_query
  - data_export
  - metadata_query
  - stored_procedure
origin: ECC
---

# Oracle数据库对接配置

## 工具信息

- 名称：Oracle Database
- 版本：19c/21c
- 类型：关系型数据库

## 连接配置

- 连接地址：jdbc:oracle:thin:@host:port:service
- 端口：1521
- 服务名：ORCL
- 认证方式：用户名/密码或Kerberos
- 只读权限：是（建议）

## 支持操作

- SQL查询
- 数据导出（CSV/JSON）
- 元数据查询
- 存储过程调用（只读）

## 接口规范

### 查询接口

```sql
SELECT * FROM table_name WHERE ROWNUM <= 1000
```

- 超时时间：5分钟
- 最大返回行数：10000
- 自动分页支持

### 导出接口

- 格式：CSV/JSON
- 压缩：支持
- 编码：UTF-8

## 特殊处理

1. **日期函数**
   - 使用 TO_CHAR 处理日期
   - 统一输出格式

2. **CLOB处理**
   - 自动转换为文本
   - 截断处理

3. **空值处理**
   - NULL转为空字符串
   - 统一空值表示

## 错误处理

- 连接失败：触发预警
- 查询超时：终止任务
- 权限不足：终止任务

## 输出格式

- 统一输出CSV格式
- 字段分隔符：逗号
- 编码：UTF-8
