# 跨库关联查询技能

## 核心功能

支持多个数据源的关联查询

## 支持场景

- Hive + MySQL 关联
- ClickHouse + MySQL 关联
- 多Hive表关联
- Hive + 本地文件关联

## 输入参数

- 数据源列表
- 关联条件
- 输出字段

## 执行方式

### 方式1：联邦查询
使用数据联邦引擎直接跨库查询

### 方式2：数据提取
1. 从数据源A提取数据
2. 从数据源B提取数据
3. 本地关联
4. 输出结果

## 注意事项

- 关联字段类型需一致
- 大量数据建议使用方式2
- 需考虑数据延迟

## 输出结果

- 关联结果数据
- 取数日志

## 依赖连接器

- connectors/datawarehouse/hive-connector.md
- connectors/datawarehouse/clickhouse-connector.md
- connectors/tool/excel-connector.md
