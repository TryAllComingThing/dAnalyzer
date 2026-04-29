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

## 执行指令

调用 `python scripts/retrieve_context.py` 执行实际检索，而非模拟检索过程：

```bash
# 检索行业指标定义和表映射
python scripts/retrieve_context.py --query "用户输入的关键词" --industry ecommerce

# 输出到文件供后续使用
python scripts/retrieve_context.py --query "配送时效" --industry logistics --output output/context.json

# 包含相关性评分
python scripts/retrieve_context.py --query "上月GMV" --industry ecommerce --include_score
```

脚本返回 JSON，包含 `indicators`（匹配的指标定义、公式、表字段映射）和 `scenarios`（场景模板）。

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
