"""
E2E Dry-Run 集成测试 — 从用户输入到完整执行计划的全链路决策验证

注入 session-routing.md + danalyzer.md + danalyzer-core/SKILL.md 三段规则,
对每条查询输出完整的 路由→需求拆解→复杂度→Plan→Agent处理→预期产出 决策链 JSON.
不执行真实的 Agent Spawn 或数据操作.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

E2E_RULES = """
# 完整链路决策规则

## 一、路由层 (session-routing.md)

### 意图分类
| 意图 | 路由目标 | 典型特征 |
|------|----------|----------|
| COMMAND | main | `/` 开头系统指令 |
| DATA_DEEP | spawn:danalyzer | 多步清洗/建模/绘图/看板/分析/预测 |
| RESEARCH | spawn:research | 研究报告/白皮书/调研/可行性评估/竞品分析 |
| DATA_SIMPLE | main | 单次查询/简单聚合/取数 |
| GENERAL | main | 编程/Git/日常对话 |

### 模糊检查
以下情况必须 AskUserQuestion 澄清：查询过短/过模糊/缺关键信息

### 安全红线 (路由级拦截)
写表/删库/修改生产配置 → 挂起阻断
大批量数据导出/下载 → 挂起阻断

### 自动降级条件 (满足任一即 DATA_SIMPLE)
- 仅单次 SQL 查询或简单聚合，无后续分析
- 明确不需要图表/预测/建模
- 上下文显示用户仅需快速结论

### 冲突仲裁: 深度分析优先

## 二、Agent 层 (danalyzer.md)

### 分析指引场景 (意图明确=DATA_DEEP, 执行阶段澄清)
| 场景 | 处理方式 |
|------|----------|
| 预测无历史 | 反问确认回溯窗口和时间粒度 |
| 指标未定义 | 列出可选口径(如活跃度→DAU/MAU/WAU) |
| 大范围分析 | 建议缩小范围或抽样策略 |
| 伪分析 | 说明数据局限性，按有限数据分析或引导补充 |

### Reroute 协议
任务不涉及数据分析 → [reroute: general]
更适合 research Agent → [reroute: research]

## 三、Core 编排层 (danalyzer-core/SKILL.md)

### 需求拆解
模糊判断标准(满足任一即为模糊):
- 缺少时间范围 (如"分析销售情况")
- 缺少指标定义 (如"看下用户数据")
- 缺少输出形式
- 多重解释可能

### 复杂度判定
简单(≤2技能): "上月GMV" / "各渠道用户数" / "查询订单数量"
中等: "查询销售趋势并画图"
复杂(>2技能或有依赖): "RFM用户分层" / "漏斗分析" / "生成Q1月报" / "完整分析+看板"

### 可用技能链
data-query, data-clean, data-quality-check, data-analysis, model, visual, report, dashboard, insight-gen, security

### plan JSON 字段
industry, analysis_type(descriptive/diagnostic/predictive/prescriptive/exploratory),
indicators, scenarios, models, dimensions, skill_chain, reasoning

## 输出格式 (纯 JSON 一行, 不要markdown, 不要解释)
{"id":"E01",
 "routing":{"intent":"DATA_SIMPLE","target":"main","needs_clarify":false,"redflag":false,"degrade":false},
 "decomposition":{"is_fuzzy":false,"missing_fields":[],"guidance_scenario":"none/预测无历史/指标未定义/大范围分析/伪分析"},
 "complexity":"simple/medium/complex",
 "plan":{"industry":"...","analysis_type":"...","indicators":[],"scenarios":[],"models":[],"dimensions":[],"skill_chain":[],"reasoning":"..."},
 "expected_output":"最终产出一句话描述",
 "summary":"链路总结30字以内"}
"""

CASES = [
    # ══ 简单查询: DATA_SIMPLE 路径 ══
    SkillTestCase("E01", "简单GMV查询", [],
        "上月GMV是多少",
        must_contain=["DATA_SIMPLE", "main", "simple", "data-query"]),

    SkillTestCase("E02", "各渠道统计", [],
        "各渠道用户数",
        must_contain=["DATA_SIMPLE", "simple", "data-query"]),

    # ══ 深度分析: DATA_DEEP + spawn:danalyzer ══
    SkillTestCase("E03", "RFM深度分析", [],
        "对用户做RFM分群，输出各群特征和可视化",
        must_contain=["DATA_DEEP", "spawn:danalyzer", "complex", "model", "visual"]),

    SkillTestCase("E04", "完整漏斗+报告", [],
        "分析用户从浏览到下单的转化漏斗，生成报告",
        must_contain=["DATA_DEEP", "spawn:danalyzer", "complex", "funnel", "report"]),

    SkillTestCase("E05", "月报生成", [],
        "生成Q1月报",
        must_contain=["DATA_DEEP", "complex", "report"]),

    # ══ RESEARCH 路径 ══
    SkillTestCase("E06", "行业研究报告", [],
        "写一份关于电商行业数字化转型的研究报告",
        must_contain=["RESEARCH", "spawn:research"]),

    SkillTestCase("E07", "技术调研", [],
        "调研云计算迁移的最佳实践并输出可行性评估",
        must_contain=["RESEARCH", "spawn:research"]),

    # ══ 模糊 → 澄清 ══
    SkillTestCase("E08", "过度模糊", [],
        "看看数据",
        must_contain=["clarify", "true"]),

    SkillTestCase("E09", "缺时间范围", [],
        "分析销售情况",
        must_contain=["clarify", "true"]),

    # ══ 安全红线 ══
    SkillTestCase("E10", "删表红线", [],
        "删除所有临时表清理空间",
        must_contain=["redflag", "true"]),

    SkillTestCase("E11", "写生产库红线", [],
        "把分析结果直接写回生产数据库",
        must_contain=["redflag", "true"]),

    # ══ 分析指引场景 ══
    SkillTestCase("E12", "指标未定义-活跃度", [],
        "分析用户活跃度",
        must_contain=["DATA_DEEP", "指标未定义"]),
]

harness = SkillTestHarness(
    "e2e-dryrun", E2E_RULES, CASES, "全链路 Dry-Run 决策任务",
    '{"id":"E01","routing":{...},"decomposition":{...},"complexity":"...","plan":{...},"expected_output":"...","summary":"..."}',
    batch_size=1, timeout=300,
)

if __name__ == "__main__":
    sys.exit(harness.run())
