"""
insight-gen Skill 单元测试 — 验证 LLM 正确执行信号检测/可信度/优先级/建议生成
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

INSIGHT_RULES = """
# 洞察提炼规则

## 1. 信号识别
| 信号 | 触发条件 |
|------|---------|
| 趋势信号 | 连续3期同向变化 或 环比>10% |
| 异常信号 | 超出IQR/3σ 或 业务合理范围外 |
| 对比信号 | 组间差异>20% |
| 结构信号 | 单一维度占比>40% |

## 2. 可信度
高(>1000样本) | 中(100-1000) | 低(<100) | 待定(无样本量)

## 3. 业务建议: 数据发现→业务含义→建议行动

## 4. 优先级
P0-紧急(>50%异常) | P1-重要(>20%影响) | P2-关注(趋势信号) | P3-信息(一般发现)

## 输出格式 (只输出纯 JSON 行, 不要 markdown, 不要解释, 不要代码块)
{"id":"I01","result":{"signals":[{"type":"trend/anomaly/comparison/structure","finding":"...","credibility":"高/中/低/待定"}],
 "recommendations":[{"action":"...","expected_effect":"...","priority":"P0/P1/P2/P3"}]},
 "summary":"..."}
"""

CASES = [
    SkillTestCase("I01", "趋势信号检测", [
        {"month": "1月", "sales": 100},
        {"month": "2月", "sales": 115},
        {"month": "3月", "sales": 132},
        {"month": "4月", "sales": 152},
    ], "分析以上销售数据的信号, 样本量=5000",
     must_contain=[]),

    SkillTestCase("I02", "异常信号检测", [
        {"day": "周一", "orders": 100},
        {"day": "周二", "orders": 95},
        {"day": "周三", "orders": 25},
        {"day": "周四", "orders": 102},
        {"day": "周五", "orders": 98},
    ], "分析以上订单数据的信号, 样本量=2000. 关注异常点",
     must_contain=[]),

    SkillTestCase("I03", "多信号优先级排序", [
        {"channel": "线上", "gmv": 5000, "users": 3000},
        {"channel": "线下", "gmv": 800, "users": 800},
        {"channel": "团购", "gmv": 600, "users": 500},
    ], "分析以上渠道数据, 识别结构信号和对比信号, 按优先级排序",
     must_contain=[]),

    SkillTestCase("I04", "无信号数据", [
        {"month": "1月", "sales": 100},
        {"month": "2月", "sales": 102},
        {"month": "3月", "sales": 98},
        {"month": "4月", "sales": 101},
    ], "分析以上数据, 波动<5%, 无明显趋势或异常. 样本量=200",
     must_contain=[]),
]

harness = SkillTestHarness(
    "insight-gen", INSIGHT_RULES, CASES, "洞察生成任务",
    '{"id":"I01","result":{"signals":[...],"recommendations":[...]},"summary":"..."}',
    batch_size=1, timeout=180,
)

if __name__ == "__main__":
    sys.exit(harness.run())
