"""
model Skill 单元测试 — 验证 LLM 正确执行 RFM/漏斗/留存等模型计算
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

MODEL_RULES = """
# 数据建模规则

## RFM 分群
R(Recency): 最近一次消费距今天数, 越小越好
F(Frequency): 消费频次, 越大越好
M(Monetary): 消费金额, 越大越好
每维度按三等分打分 1-3, 加权后分群: 高价值(R高+F高+M高), 保持(R高+F低+M高), 流失(R低+F低+M低)

## 漏斗分析
每步转化率=当前步/上一步*100%, 关键看最大流失环节

## 留存分析
第N日留存率=第N日活跃/首日活跃*100%, 关注留存曲线拐点

## 预测
输出必须含: 预测值+置信区间+假设条件+风险提示
"""

CASES = [
    SkillTestCase("M01", "RFM分群", [
        {"user": "U1", "last_order_days": 5, "order_count": 20, "total_amount": 5000},
        {"user": "U2", "last_order_days": 90, "order_count": 2, "total_amount": 200},
        {"user": "U3", "last_order_days": 10, "order_count": 15, "total_amount": 3000},
        {"user": "U4", "last_order_days": 3, "order_count": 30, "total_amount": 8000},
        {"user": "U5", "last_order_days": 60, "order_count": 5, "total_amount": 800},
    ], "对以上用户做 RFM 分群, 每维度分 1-3 分, 输出分群结果",
     must_contain=[]),

    SkillTestCase("M02", "漏斗分析", [
        {"step": "访问", "users": 10000},
        {"step": "加购", "users": 3000},
        {"step": "下单", "users": 1500},
        {"step": "支付", "users": 1200},
        {"step": "复购", "users": 400},
    ], "分析漏斗转化率, 找出最大流失环节",
     must_contain=[]),

    SkillTestCase("M03", "留存分析", [
        {"day": 0, "active": 1000},
        {"day": 1, "active": 500},
        {"day": 3, "active": 350},
        {"day": 7, "active": 250},
        {"day": 14, "active": 200},
        {"day": 30, "active": 150},
    ], "计算各天留存率, 分析留存曲线特征",
     must_contain=[]),

    SkillTestCase("M04", "场景预测", [
        {"month": "2024-01", "sales": 100}, {"month": "2024-02", "sales": 110},
        {"month": "2024-03", "sales": 105}, {"month": "2024-04", "sales": 120},
        {"month": "2024-05", "sales": 115}, {"month": "2024-06", "sales": 130},
    ], "基于历史趋势预测 2024-07 的 sales, 给出置信区间和假设条件",
     must_contain=[]),
]

harness = SkillTestHarness(
    "model", MODEL_RULES, CASES, "建模任务",
    '{"id":"M01","result":{},"summary":"..."}',
    batch_size=1, timeout=300,
)

if __name__ == "__main__":
    sys.exit(harness.run())
