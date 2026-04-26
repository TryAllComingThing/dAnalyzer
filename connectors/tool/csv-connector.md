---
name: csv-connector
description: CSV文件对接配置，支持读取、写入和追加CSV数据
type: tool
capabilities:
  - csv_read
  - csv_write
  - csv_append
  - delimiter_detection
origin: ECC
---

# CSV文件对接配置

## 工具信息

- 名称：CSV文件
- 类型：文件数据源
- 编码：UTF-8

## 连接配置

- 文件路径：支持绝对/相对路径
- 分隔符：逗号(,) / 制表符(\t) / 分号(;)
- 字符集：UTF-8 / GBK
- 表头：第一行作为字段名

## 支持操作

- 读取CSV文件
- 写入CSV文件
- 追加数据

## 接口规范

### 读取接口

```csv
column1,column2,column3
value1,value2,value3
```

- 自动识别分隔符
- 支持压缩文件（.csv.gz）
- 最大文件大小：100MB

### 写入接口

- 支持指定分隔符
- 支持写入表头
- 支持追加模式

## 字段类型识别

| 类型 | 示例 | 识别方式 |
|------|------|----------|
| 字符串 | abc | 非数字 |
| 整数 | 123 | 纯数字 |
| 浮点数 | 123.45 | 含小数点 |
| 日期 | 2026-04-24 | 日期格式 |
| 布尔 | true/false | 逻辑值 |

## 错误处理

- 文件不存在：报错
- 编码错误：尝试自动转换
- 格式错误：跳过并记录

## 输出格式

- 统一输出为DataFrame/Table格式
- 字段名来自表头
