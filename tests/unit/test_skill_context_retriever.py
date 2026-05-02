"""
context-retriever Skill 单元测试 — 验证 LLM 正确进行意图路由和上下文检索
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

CONTEXT_RULES = """
# 意图路由规则

## 分析类型
- descriptive: 描述性（是什么）- 销售概况/用户概况/订单概况/品类/渠道/区域/新品/利润
- diagnostic: 诊断性（为什么）- 归因分析/下降诊断/异常分析
- predictive: 预测性（将怎样）- 预测/预估/趋势预判
- prescriptive: 规范性（怎么办）- 建议/策略/优化方案
- exploratory: 探索性（还发现什么）- 分群/RFM/漏斗/留存/购物篮/动销

## 行业关键词映射
- 销售/营收/GMV/业绩/卖了 → sales_amount, order_count
- 用户/消费者/会员 → user_id, order_count
- 毛利/毛利率/净利/利润 → gross_profit, gross_margin_rate, net_profit
- 转化/转化率 → conversion_rate
- 动销/售罄 → sell_through_rate
- 库存/周转 → inventory_turnover, inventory_days
- 退货/退款 → return_rate
- 促销/活动 → promotion_roi, coupon_usage_rate
- 渠道/经销商 → sales_amount, order_count
- 分群/RFM/聚类 → order_count, sales_amount, user_id

## 路由决策
1. 提取用户查询中的行业关键词 → 确定 industry
2. 确定分析类型 (descriptive/diagnostic/predictive/prescriptive/exploratory)
3. 匹配 intent (优先级从上到下，排除 negative_keywords 命中的 intent)
4. 确定 indicators / scenarios / models / skill_chain

## 输出格式
每行一个 JSON:
{"id":"CR01","intent_id":"...","analysis_type":"...","indicators":["..."],
 "scenarios":["..."],"skill_chain":["..."],"industry":"fmcg",
 "confidence":0.0,"summary":"..."}
"""

CASES = [
    SkillTestCase("CR01", "描述性-销售概况", [],
        "展示今年的销售业绩情况, 包括GMV和订单量",
        must_contain=["descriptive", "sales_amount", "order_count"]),

    SkillTestCase("CR02", "诊断性-销售下降", [],
        "为什么最近销售额一直在下滑？帮我分析一下原因",
        must_contain=["diagnostic", "sales_amount"]),

    SkillTestCase("CR03", "预测性-销售预测", [],
        "预测下个月GMV能达到多少？根据历史趋势预判",
        must_contain=["predictive"]),

    SkillTestCase("CR04", "规范性-提升建议", [],
        "如何提升转化率？给些优化建议和策略方案",
        must_contain=["prescriptive", "conversion_rate"]),

    SkillTestCase("CR05", "探索性-用户分群", [],
        "帮我做一下用户分群分析，看看客群结构",
        must_contain=["exploratory", "user_id"]),

    SkillTestCase("CR06", "利润诊断", [],
        "毛利一直下降，到底什么原因导致的",
        must_contain=["diagnostic", "gross_profit"]),

    SkillTestCase("CR07", "行业识别-快消", [],
        "分析快消品的SKU动销情况和库存周转天数",
        must_contain=["fmcg", "sell_through_rate", "inventory_turnover"]),
]

harness = SkillTestHarness(
    "context-retriever", CONTEXT_RULES, CASES, "意图路由任务",
    '{"id":"<用例ID>","intent_id":"...","analysis_type":"...","indicators":["..."],'
    '"scenarios":["..."],"skill_chain":["..."],"industry":"fmcg",'
    '"confidence":0.0,"summary":"..."}',
    batch_size=1, timeout=300,
)

if __name__ == "__main__":
    sys.exit(harness.run())
