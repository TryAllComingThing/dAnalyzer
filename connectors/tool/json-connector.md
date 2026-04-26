---
name: json-connector
description: JSON文件对接配置，支持读取、写入JSON和JSONPath查询
type: tool
capabilities:
  - json_read
  - json_write
  - jsonpath_query
  - nested_field_flatten
origin: ECC
---

# JSON文件对接配置

## 工具信息

- 名称：JSON文件
- 类型：文件数据源
- 编码：UTF-8

## 连接配置

- 文件路径：支持绝对/相对路径
- 编码：UTF-8
- 支持压缩：.json.gz

## 支持操作

- 读取JSON文件
- 写入JSON文件
- JSON路径查询

## 接口规范

### 读取接口

支持格式：

**数组格式**
```json
[
  {"id": 1, "name": "Alice"},
  {"id": 2, "name": "Bob"}
]
```

**对象格式**
```json
{
  "data": [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}
  ],
  "total": 2
}
```

### 查询接口

- 支持JSONPath查询
- 支持过滤条件
- 支持字段选择

## 字段处理

- 嵌套字段：扁平化为 parent_child
- 数组字段：转为JSON字符串存储
- 空值：转为null

## 错误处理

- 文件不存在：报错
- 格式错误：报错并提示位置
- 编码错误：尝试自动转换

## 输出格式

- 统一输出为DataFrame/Table格式
- 字段名处理嵌套结构

## 使用场景

- 配置文件读取
- API响应解析
- 日志文件处理
