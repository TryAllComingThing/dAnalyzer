"""
research-core Skill 单元测试 — 验证研究深度分级/抗幻觉/写作标准/质量清单
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

RESEARCH_RULES = """
# 研究方法论规则

## 研究深度分级
- L1 快速研究: "了解"/"概述"/"简介"/"大致说说" → >=10来源, 2000+字
- L2 深度研究: "趋势"/"分析"/"影响"（默认） → >=20来源, 6000+字
- L3 专家级研究: "全面"/"系统"/"专业"/"决策依据" → >=30来源, 10000+字
- 未指定时默认 L2

## 抗幻觉协议
- 每个事实性论断附带 [N] 内联引用
- 推测必须明确标注 "如果该趋势持续..."/"可能..."
- 禁止 "研究表明..." 不带具体引用
- 禁止编造来源填补空白
- 不确定时说 "未找到直接涉及 X 的公开来源"

## 写作标准
- 叙事散文优先，禁止要点作为主体内容
- 每个 ## 标题下 >=3 段完整散文
- 要点占比 <20%
- 关键发现放在每节开头或结尾

## 质量验证清单
- 摘要 50-250 字
- 必需章节: 执行摘要 → 正文 → 结论与建议 → 局限性 → 附录
- 引用格式统一为 [N]
- 无占位符 (TBD/TODO/内容待补充)
- 所有统计数据标注年份/时间范围

## 输出格式
每行一个 JSON:
{"id":"RC01","depth_level":"L1/L2/L3","has_citations":true/false,
 "has_limitations":true/false,"quality_checks_passed":N,
 "summary":"..."}
"""

CASES = [
    SkillTestCase("RC01", "L1快速研究触发词", [],
        "根据以下用户查询判断应使用哪个研究深度级别(只判断级别,不做实际研究): '大致了解下快消品市场，给个概述就行'",
        must_contain=["L1"]),

    SkillTestCase("RC02", "L2深度研究默认", [],
        "根据以下用户查询判断应使用哪个研究深度级别(只判断级别,不做实际研究): '分析快消品电商的发展趋势和竞争格局'",
        must_contain=["L2"]),

    SkillTestCase("RC03", "L3专家级触发词", [],
        "根据以下用户查询判断应使用哪个研究深度级别(只判断级别,不做实际研究): '做一个全面的系统的专业的市场研究,用于决策依据'",
        must_contain=["L3"]),

    SkillTestCase("RC04", "抗幻觉-引用格式", [],
        "根据研究方法论规则，事实性论断应如何标注来源？说明引用格式和反例",
        must_contain=["[N]", "引用"],
        must_not=["研究表明市场规模", "专家认为", "多个来源证实"]),
]

harness = SkillTestHarness(
    "research-core", RESEARCH_RULES, CASES, "研究任务",
    '{"id":"<用例ID>","depth_level":"L1/L2/L3","has_citations":true/false,'
    '"has_limitations":true/false,"quality_checks_passed":N,'
    '"summary":"..."}',
    batch_size=1, timeout=120,
)

if __name__ == "__main__":
    sys.exit(harness.run())
