"""
report Skill 单元测试 — 验证 LLM 正确生成结构化报告 (类型/指标/环比/异常标记)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

REPORT_RULES = """
# 报告生成规则

## 报告类型
日报: 今日概览→核心KPI→趋势→异常/亮点→关注事项
周报: 本周摘要→核心指标趋势(含环比)→维度拆解→TOP榜单→异常→下周关注

## 核心指标
GMV=SUM(actual_amount), 订单量=COUNT(order_id), 客单价=GMV/订单量
环比=(本期-上期)/上期×100%

## 变化判定
≤5%持平 | 5-10%小幅↑↓ | 10-20%显著↑↓ | >20%大幅↑↓ | >50%异常↑↓

## 输出格式 (必须是纯 JSON, 不要输出 markdown)
{"id":"R01","report_type":"日报","sections":["概览","KPI","趋势","关注事项"],
 "metrics":{"gmv":0,"orders":0,"arpu":0},"anomalies":[...],"summary":"..."}
"""

CASES = [
    SkillTestCase("R01", "日报生成", [
        {"date": "2024-06-01", "gmv": 12000, "orders": 120, "users": 1000, "refund": 3},
    ], "生成一份日报, 包含今日概览、核心KPI、趋势、关注事项",
     must_contain=["日报", "GMV", "KPI"]),

    SkillTestCase("R02", "环比计算与标记", [
        {"period": "上周", "gmv": 10000, "orders": 100},
        {"period": "本周", "gmv": 11500, "orders": 115},
    ], "计算本周vs上周的环比变化, 标记变化幅度",
     must_contain=["15", "%", "显著"]),

    SkillTestCase("R03", "异常标记", [
        {"period": "上周", "gmv": 10000},
        {"period": "本周", "gmv": 4000},
    ], "本周GMV下降60%, 生成报告异常章节",
     must_contain=["异常", "60%", "大幅"]),
]

harness = SkillTestHarness(
    "report", REPORT_RULES, CASES, "报告生成任务",
    '{"id":"R01","report_type":"...","sections":[...],"metrics":{...},"anomalies":[...],"summary":"..."}',
    timeout=180,
)

if __name__ == "__main__":
    sys.exit(harness.run())
