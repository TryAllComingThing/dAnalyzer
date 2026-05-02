"""
danalyzer-core 编排器集成测试 — 需求拆解 + 复杂度判定 + 技能链编排
验证 Section II (需求拆解/模糊判断) 和 Section III (复杂度判定/技能链选择)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

CORE_RULES = """
# dAnalyzer Core — 编排调度器

## 需求拆解

### 模糊判断标准
满足任一即判定为"需求模糊"，必须 AskUserQuestion 澄清：
- 缺少时间范围（如"分析销售情况"未说明近7天/本月/全年）
- 缺少指标定义（如"看下用户数据"未说明看什么指标）
- 缺少输出形式（如"分析下数据"未说明要图表/报告/表格）
- 多重解释可能（如"分析产品"指销量、评价还是库存？）

### 分析指引场景（意图明确，执行阶段澄清）
以下场景意图已明确为 DATA_DEEP，不在需求拆解阶段触发 AskUserQuestion：
- 预测无历史：要求预测但未提供历史数据范围 → 先反问确认回溯窗口
- 指标未定义：指标有多个业务口径（如"活跃度"可选 DAU/MAU/WAU）
- 大范围分析：时间跨度极大
- 伪分析：无数据或仅片段数据但要求深度分析

## 复杂度判定

| 请求示例 | 判定 | 处理方式 |
|----------|------|----------|
| "查询订单数量" | 简单 | data-query → security |
| "上月GMV" | 简单 | data-query → security |
| "各渠道用户数" | 简单 | data-query → security |
| "查询销售趋势并画图" | 中等 | data-query → data-analysis → visual → security |
| "分析上个月销售趋势" | 复杂 | 需求拆解 → 多技能编排 |
| "RFM用户分层" | 复杂 | 需求拆解 → 多技能编排 |
| "漏斗分析" | 复杂 | 需求拆解 → 多技能编排 |
| "生成Q1月报" | 复杂 | 需求拆解 → 多技能编排 |

决策规则：明确+简单(≤2技能)→直接执行 | 明确+复杂(>2技能)→先出计划 | 模糊→先澄清

## 可用技能
data-query, data-clean, data-quality-check, data-analysis, model, visual, report, dashboard, insight-gen, security

## 输出格式 (纯 JSON, 一行)
{"id":"O01","needs_clarify":false,"complexity":"simple/medium/complex","skill_chain":["data-query","security"],"reasoning":"理由20字以内","summary":"一句话"}
"""

CASES = [
    # ══ 明确 + 简单 ══
    SkillTestCase("O01", "明确简单-直接查询", [],
        "上月GMV是多少",
        must_contain=["simple", "data-query", "security"]),

    SkillTestCase("O02", "明确简单-渠道统计", [],
        "各渠道用户数",
        must_contain=["simple", "data-query"]),

    # ══ 模糊需澄清 ══
    SkillTestCase("O03", "模糊-缺时间范围", [],
        "分析销售情况",
        must_contain=["clarify", "true"]),

    SkillTestCase("O04", "模糊-什么都缺", [],
        "看看数据",
        must_contain=["clarify", "true"]),

    SkillTestCase("O05", "模糊-缺输出形式", [],
        "分析下数据",
        must_contain=["clarify", "true"]),

    # ══ 明确 + 复杂 ══
    SkillTestCase("O06", "明确复杂-RFM分群", [],
        "RFM用户分层",
        must_contain=["complex", "model"]),

    SkillTestCase("O07", "明确复杂-漏斗分析", [],
        "完整漏斗分析并生成报告",
        must_contain=["complex", "report"]),

    SkillTestCase("O08", "明确复杂-月报", [],
        "生成Q1月报",
        must_contain=["complex", "report"]),

    # ══ 中等 ══
    SkillTestCase("O09", "中等-趋势图", [],
        "查询销售趋势并画图",
        must_contain=["data-analysis", "visual"]),

    # ══ 分析指引场景（意图明确，不触发 AskUserQuestion） ══
    SkillTestCase("O10", "分析指引-指标未定义", [],
        "分析用户活跃度",
        must_contain=["complex"]),
]

harness = SkillTestHarness(
    "core-orchestrator", CORE_RULES, CASES, "需求拆解与复杂度判定任务",
    '{"id":"O01","needs_clarify":false,"complexity":"simple","skill_chain":[...],"reasoning":"...","summary":"..."}',
    batch_size=1, timeout=180,
)

if __name__ == "__main__":
    sys.exit(harness.run())
