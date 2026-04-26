# 时间范围取数技能

## 核心功能

按指定时间范围取数

## 时间类型

- 日：YYYY-MM-DD
- 周：YYYY年第N周
- 月：YYYY-MM
- 季度：YYYYQN
- 年：YYYY
- 自定义范围

## 输入参数

- 表名
- 时间字段
- 时间范围
- 筛选字段
- 输出字段

## 执行逻辑

1. 解析时间参数
2. 生成时间过滤条件
3. 执行查询
4. 返回结果

## 输出结果

- 数据文件
- 取数日志

## 依赖规则

- rules/core/dimension-standard.md
- rules/base/sql-write.md
