---
name: context-retriever
description: 行业上下文检索 — 通过 IndustryStore 查询行业指标、表映射、分析模板
---

# 动态上下文检索器 (Context Retriever)

## When to Activate

- Use this skill when generating SQL queries that require industry-specific knowledge
- Use this skill when user input contains industry-specific terms
- Use this skill before executing data-query skill to inject industry context

## 核心能力

### 1. 指标检索 (Indicator Retrieval)

通过 IndustryStore.search() 检索行业指标定义、公式、表映射。

```
输入: "配送时效" → IndustryStore("logistics").search("配送时效")
返回: [{name: "平均配送时长", formula: "AVG(delivery_hours)", ...}]
```

### 2. 场景模板检索

检索行业分析场景模板（场景定义、所需指标、分析维度）。

## 执行指令

调用 `python scripts/retrieve_context.py` 或直接使用 IndustryStore：

```python
from scripts.industry.store import IndustryStore
store = IndustryStore("ecommerce")
results = store.search("GMV")
```

脚本接口：

```bash
python scripts/retrieve_context.py --query "关键词" --industry ecommerce
```

返回 JSON: `{"indicators": [...], "scenarios": [...]}`

## 依赖

- scripts/industry/store.py — IndustryStore 存储引擎
- scripts/industry/retriever.py — IndustryRetriever 高级检索（RRF/向量）
- data/industry/{industry}/ — 行业 YAML 配置
