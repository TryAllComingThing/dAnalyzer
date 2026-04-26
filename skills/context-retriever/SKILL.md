---
name: context-retriever
description: 动态上下文检索，根据用户输入检索相关的指标定义、表结构映射、分析模板
---

# 动态上下文检索器 (Context Retriever)

## When to Activate

- Use this skill when needing to understand what indicators or metrics the user refers to
- Use this skill when generating SQL queries that require industry-specific knowledge
- Use this skill when user input contains industry-specific terms (e.g., "配送时效" in logistics)
- Use this skill before executing data-query skill to inject industry context

## Core Functionality

### 1. 指标检索 (Indicator Retrieval)

根据用户输入，从行业配置中检索相关指标：

```
输入: "配送时效"
行业: logistics

检索过程:
1. 在 data/industry/{行业}/indicators/ 目录搜索
2. 匹配指标名称、关键词
3. 返回相关性最高的指标及其完整定义
```

### 2. 表映射检索 (Mapping Retrieval)

根据识别的指标，检索对应的数据库表和字段：

```
输入指标: avg_delivery_time
行业: logistics

检索过程:
1. 查找指标关联的表
2. 提取字段映射（中文字段 → 英文字段）
3. 提取指标计算公式
```

### 3. 时间解析 (Time Parsing)

解析用户输入中的时间范围：

```
输入: "上月"、"过去7天"、"本周"
解析结果: {start: "2026-03-01", end: "2026-03-31", granularity: "day"}
```

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_input | string | Yes | 用户输入的自然语言 |
| industry | string | Yes | 行业代码 (ecommerce/logistics/manufacturing/finance) |
| retrieval_scope | string | No | 检索范围: all/indicators/mappings/templates |
| max_results | number | No | 最大返回结果数，默认 5 |

## Retrieval Process

### Step 1: 关键词提取

```
用户输入: "查询上月各地区配送时效"

提取关键词:
- "配送" (高权重)
- "时效" (高权重)
- "地区" (维度)
- "上月" (时间)
```

### Step 2: 行业配置检索

```
基于行业代码，读取配置文件:

data/industry/{industry}/
├── indicators/           # 指标定义
│   ├── _index.yaml        # 指标索引
│   └── delivery.yaml     # 配送相关指标
├── mappings/             # 表映射
│   └── delivery-mapping.yaml
└── templates/            # 分析模板
    └── delivery-analysis.yaml
```

### Step 3: 关键词匹配

在索引文件中搜索匹配的指标：

```
关键词: "配送时效"

匹配过程:
1. 在 _index.yaml 的 keyword_index 中搜索
2. "配送" → [avg_delivery_time, on_time_delivery_rate, delivery_count]
3. "时效" → [avg_delivery_time, on_time_delivery_rate]
4. 合并结果，按相关度排序
```

### Step 4: 获取完整定义

对于每个匹配的指标，获取完整定义：

```
指标: avg_delivery_time

获取:
- name: 平均配送时长
- definition: 订单从下达到完成配送的平均时长
- calculation: AVG(TIMESTAMPDIFF(HOUR, order_time, delivery_time))
- unit: 小时
- related_table: delivery_orders
```

## Output Format

```json
{
  "status": "success",
  "industry": "logistics",
  "retrieved": {
    "indicators": [
      {
        "key": "avg_delivery_time",
        "name": "平均配送时长",
        "definition": "订单从下达到完成配送的平均时长",
        "calculation": "AVG(TIMESTAMPDIFF(HOUR, order_time, delivery_time))",
        "unit": "小时",
        "relevance": 0.95,
        "source_file": "indicators/delivery.yaml",
        "related_table": "delivery_orders"
      }
    ],
    "mappings": [
      {
        "table": "delivery_orders",
        "fields": {
          "配送时长": "duration_hours",
          "下单时间": "order_time",
          "配送完成时间": "delivery_time",
          "是否准时": "is_on_time",
          "地区": "region"
        },
        "metrics": {
          "平均配送时长": "AVG(duration_hours)",
          "准时交付率": "SUM(CASE WHEN is_on_time=1 THEN 1 ELSE 0 END) / COUNT(*)"
        }
      }
    ],
    "time": {
      "上月": {
        "start_date": "2026-03-01",
        "end_date": "2026-03-31",
        "granularity": "month"
      }
    },
    "dimensions": [
      {"key": "region", "name": "地区", "values": null}
    ]
  },
  "context_summary": "已检索到配送时效相关指标：平均配送时长(avg_delivery_time)，使用delivery_orders表，通过region维度分组"
}
```

## Usage Example

### Example 1: 配送时效查询

```
用户输入: "查询上月各地区配送时效"

输入参数:
{
  "user_input": "查询上月各地区配送时效",
  "industry": "logistics"
}

检索结果:
- 指标: 平均配送时长 (avg_delivery_time)
- 表: delivery_orders
- 字段: duration_hours, region, order_time
- 时间: 上月 (2026-03-01 ~ 2026-03-31)
- 维度: 地区 (region)

生成的 SQL 提示:
SELECT
    region,
    AVG(duration_hours) as avg_delivery_time
FROM delivery_orders
WHERE order_time >= '2026-03-01' AND order_time < '2026-04-01'
GROUP BY region
```

### Example 2: 销售趋势查询

```
用户输入: "查看本月销售趋势"

输入参数:
{
  "user_input": "查看本月销售趋势",
  "industry": "ecommerce"
}

检索结果:
- 指标: 销售额 (sales_amount)
- 表: orders
- 字段: order_amount, order_date
- 时间: 本月
- 维度: 时间
```

### Example 3: 生产效率查询

```
用户输入: "查询本周产能利用率"

输入参数:
{
  "user_input": "查询本周产能利用率",
  "industry": "manufacturing"
}

检索结果:
- 指标: 产能利用率 (capacity_utilization)
- 表: production_orders
- 字段: actual_quantity, planned_quantity, production_line
- 时间: 本周
```

## Index File Format

### indicators/_index.yaml

```yaml
---
category: delivery
total_count: 15
---

index:
  - key: avg_delivery_time
    name: 平均配送时长
    keywords: [配送时长, 配送时间, 时效, 多久]
    related_tables: [delivery_orders]

  - key: on_time_delivery_rate
    name: 准时交付率
    keywords: [准时率, 准时交付, 妥投率]
    related_tables: [delivery_orders]

  - key: delivery_count
    name: 配送订单量
    keywords: [配送量, 订单数, 配送单量]
    related_tables: [delivery_orders]

# 关键词到指标的映射
keyword_index:
  配送: [avg_delivery_time, on_time_delivery_rate, delivery_count]
  时效: [avg_delivery_time, on_time_delivery_rate]
  订单: [delivery_count]
  准时: [on_time_delivery_rate]
```

## Integration with Other Skills

### 在 data-query 中使用

```
在执行 NL2SQL 之前:

1. 调用 context-retriever skill
   输入: user_input + industry

2. 获取检索结果:
   - indicators: 指标定义
   - mappings: 表字段映射
   - time: 时间范围
   - dimensions: 分组维度

3. 将检索结果注入 NL2SQL prompt:
   - 指标定义 → 告诉 LLM 每个指标的计算方式
   - 表映射 → 告诉 LLM 如何映射中文到英文字段
   - 时间范围 → 添加 WHERE 条件

4. 生成准确 SQL
```

### 在 danalyzer-core 中触发

```
判断是否需要触发 context-retriever:
- 用户输入包含行业特征词? (如"配送"、"销售"、"产能")
- 需要生成 SQL?
- 尚未加载行业上下文?

满足条件时:
→ 调用 context-retriever
→ 将结果传递给 data-query
```

## Error Handling

| Error | Handling |
|-------|----------|
| 行业配置不存在 | 返回错误提示，建议检查行业代码 |
| 索引文件不存在 | 提示需要创建索引文件 |
| 检索无结果 | 返回空结果，可使用通用查询 |
| 指标定义不完整 | 返回部分信息 + 警告 |

## Dependencies

- data/industry/{industry}/indicators/ - 指标定义目录
- data/industry/{industry}/mappings/ - 表映射目录
- data/industry/{industry}/templates/ - 分析模板目录
- data/industry/_base/keywords.yaml - 行业关键词（用于识别行业）

## Notes

1. 检索是**按需**的，只在需要行业知识时触发
2. 检索结果可以**缓存**，避免重复检索
3. 索引文件 (_index.yaml) 是检索性能的关键
4. 支持**模糊匹配**，处理用户表达的多样性
