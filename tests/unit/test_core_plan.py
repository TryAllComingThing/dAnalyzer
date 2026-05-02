"""
danalyzer-core Step 2.5 集成测试 — 结构化分析计划 JSON 生成
验证 LLM 正确使用 context-card 中的真实 code 生成 plan JSON
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

PLAN_RULES = """
# 结构化分析计划生成规则

## Step 2.5b: 输出分析计划 JSON

根据 context-card 中的真实 code 列表填写。严格 JSON，无额外文字。

## context-card (当前可用的真实资源)

```yaml
industries:
  fmcg:
    label: 快消
    indicators:
      - code: sales_amount
        label: 销售额
      - code: order_count
        label: 订单量
      - code: gmv
        label: GMV
      - code: customer_count
        label: 客户数
      - code: repurchase_rate
        label: 复购率
      - code: conversion_rate
        label: 转化率
      - code: arpu
        label: 客单价
      - code: retention_rate
        label: 留存率
    scenarios:
      - code: sales_trend
        label: 销售趋势
      - code: channel_comparison
        label: 渠道对比
      - code: customer_analysis
        label: 客户分析
      - code: product_ranking
        label: 商品排行
    models:
      - rfm-model
      - funnel-model
      - attribution-model
      - forecasting-model
      - cohort-analysis
      - clustering-model

  ecommerce:
    label: 电商
    indicators:
      - code: gmv
        label: GMV
      - code: order_count
        label: 订单量
      - code: conversion_rate
        label: 转化率
      - code: cart_abandon_rate
        label: 购物车放弃率
      - code: customer_acquisition_cost
        label: 获客成本
    scenarios:
      - code: promotion_analysis
        label: 大促分析
      - code: traffic_analysis
        label: 流量分析
      - code: customer_analysis
        label: 客户分析
    models:
      - funnel-model
      - rfm-model
      - attribution-model

analysis_type_mapping:
  descriptive: [data-query, data-clean, data-analysis, visual, security]
  diagnostic: [data-query, data-clean, data-analysis, model, visual, report, security]
  predictive: [data-query, data-clean, data-analysis, model, visual, report, security]
  prescriptive: [data-query, data-clean, data-analysis, model, visual, report, security]
  exploratory: [data-query, data-clean, data-analysis, visual, report, security]
```

## plan JSON 格式

{
  "industry": "从context-card匹配",
  "intent_id": "描述意图的snake_case id",
  "analysis_type": "descriptive/diagnostic/predictive/prescriptive/exploratory",
  "confidence": 0.0-1.0,
  "indicators": ["必须使用context-card中存在的indicator_code"],
  "scenarios": ["必须使用context-card中存在的scenario_code"],
  "models": ["参考context-card中的models"],
  "dimensions": ["category","time","channel"等],
  "skill_chain": ["参考analysis_type_mapping"],
  "reasoning": "简短理由"
}

字段填值规则：
- indicators 必须使用 context-card 中存在的 indicator_code，至少 2 个
- scenarios 必须使用 context-card 中存在的 scenario_code，至少 1 个
- models 参考 context-card 中存在的模型名
- skill_chain 参考 analysis_type_mapping，以 security 结尾

## 输出格式 (纯 JSON, 一行, 不要 markdown)
"""

CASES = [
    SkillTestCase("P01", "FMCG销售诊断", [],
        "分析快消品类销售下滑的原因",
        must_contain=["fmcg", "sales_amount", "sales_trend", "diagnostic", "attribution-model"]),

    SkillTestCase("P02", "电商客户RFM", [],
        "对电商用户做RFM分群",
        must_contain=["ecommerce", "rfm-model", "model", "gmv"]),

    SkillTestCase("P03", "简单查询", [],
        "上月GMV",
        must_contain=["gmv", "descriptive", "data-query"]),

    SkillTestCase("P04", "转化漏斗分析", [],
        "分析用户从浏览到下单的转化漏斗",
        must_contain=["conversion_rate", "funnel-model", "diagnostic"]),

    SkillTestCase("P05", "渠道对比", [],
        "对比各渠道的GMV和订单量",
        must_contain=["channel_comparison", "gmv", "order_count"]),
]

harness = SkillTestHarness(
    "core-plan", PLAN_RULES, CASES, "分析计划生成任务",
    '{"id":"P01","industry":"...","analysis_type":"...","indicators":[...],"scenarios":[...],"models":[...],"skill_chain":[...],"reasoning":"...","summary":"..."}',
    batch_size=1, timeout=180,
)

if __name__ == "__main__":
    sys.exit(harness.run())
