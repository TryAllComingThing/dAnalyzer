---
name: query
description: 高级查询技能，支持跨库关联、时间区间查询、聚合查询、漏斗查询等
---

# 查询技能 (Query)

## When to Activate

- Use this skill when querying data or running complex queries
- Use this skill when performing cross-database joins
- Use this skill when doing aggregation queries (SUM, AVG, COUNT, etc.)
- Use this skill when analyzing funnel data or conversion data
- Use this skill when performing cohort analysis queries
- Use this skill when working with time range queries

## 核心能力

1. **聚合查询** - SUM/AVG/COUNT/MAX/MIN
2. **跨库关联** - 多数据源JOIN
3. **队列查询** - 同期群数据查询
4. **漏斗查询** - 转化步骤数据
5. **多源查询** - Hive/ClickHouse/MySQL
6. **时间区间** - 灵活时间范围

## 子技能

| 子技能 | 文件 | 说明 |
|--------|------|------|
| 聚合查询 | aggregation-query.md | 统计聚合 |
| 队列查询 | cohort-query.md | 同期群查询 |
| 跨库关联 | cross-db-join.md | 多数据源JOIN |
| 漏斗查询 | funnel-query.md | 转化漏斗数据 |
| 多源查询 | multi-source-query.md | 多数据源查询 |
| 时间区间 | time-range-query.md | 时间范围查询 |

## 使用场景

### 场景1: 复杂统计
```
用户: 按月统计销售额和订单量
→ 调用 query 技能 → 聚合查询
→ 按月分组聚合
→ 输出统计结果
```

### 场景2: 跨库分析
```
用户: 关联Hive和MySQL数据
→ 调用 query 技能 → 跨库关联
→ 执行跨库JOIN
→ 输出关联结果
```

## 依赖配置

- skills/data-query - 基础查询
- connectors/datawarehouse/ - 数仓连接
- rules/core/indicator-caliber.md - 指标口径
