---
name: excel-connector
description: Microsoft Excel对接配置，支持读取、写入Excel数据和公式计算
type: tool
capabilities:
  - excel_read
  - excel_write
  - formula_calculation
  - format_setting
origin: ECC
---

# Excel辅助工具对接配置

## 工具信息

- 名称：Microsoft Excel
- 版本：Office 365
- 类型：辅助工具

## 连接配置

- 文件路径：支持本地文件路径
- 并发限制：3个文件同时处理
- 支持格式：.xlsx、.xls、.csv

## 支持操作

- 读取Excel数据
- 写入Excel数据
- 格式设置
- 公式计算

## 接口规范

### 读取接口

- 支持多Sheet读取
- 自动识别数据类型
- 最大读取行数：1048576

### 写入接口

- 支持写入公式
- 支持格式设置
- 自动保存

## 错误处理

- 文件不存在：终止任务
- 格式错误：预警
- 写入失败：重试1次

## 输出格式

- Excel格式（.xlsx）
- CSV格式（.csv）
