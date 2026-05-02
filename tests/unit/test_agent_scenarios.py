"""
danalyzer Agent 集成测试 — 分析指引场景处理 + 错误策略 + Reroute 协议
验证 danalyzer.md 执行协议中 Agent 的决策逻辑
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

AGENT_RULES = """
# danalyzer Agent — 执行协议

## 分析指引场景处理
以下场景意图已明确（DATA_DEEP），不触发 AskUserQuestion 在路由阶段，
由 Agent 在执行阶段主动澄清后继续：

| 场景 | 处理方式 |
|------|----------|
| 预测无历史 | 先反问确认回溯窗口和时间粒度，确认后继续 |
| 指标未定义 | 列出可选口径让用户选择（如"活跃度"可选 DAU/MAU/WAU） |
| 大范围分析 | 建议缩小范围或抽样策略，用户确认后执行 |
| 伪分析 | 说明数据局限性，按有限数据做分析或引导补充数据 |

## 错误处理策略

| 错误类型 | 严重程度 | 默认策略 |
|----------|----------|----------|
| 取数超时 | 可恢复 | retry（最多3次，指数退避） |
| 数据为空 | 警告 | skip（记录警告，继续下一个） |
| 格式错误 | 可恢复 | retry（1次） |
| 权限不足 | 致命 | abort（中止任务，报告错误） |
| 规则违规 | 致命 | abort（中止任务，报告错误） |
| 资源不足 | 可恢复 | retry（2次） |

## Reroute 协议
当 Agent 发现任务不属于数据分析职责范围时，输出重路由指令：
- [reroute: research] — 重路由到 research agent
- [reroute: general] — 重路由到主会话直接处理

触发条件：
- 用户请求不涉及数据分析（编程、Git操作、日常对话）
- 更适合其他 Agent
- 数据源不存在或任务超出能力边界

## 输出格式
{"id":"A01","scenario":"预测无历史/指标未定义/大范围分析/伪分析/错误处理/reroute",
 "action":"反问确认/列出选项/建议缩小/说明局限/retry/skip/abort/reroute:general/reroute:research",
 "detail":"具体处理说明20字以内","summary":"一句话"}
"""

CASES = [
    # ══ 分析指引场景 ══
    SkillTestCase("A01", "预测无历史", [],
        "用户要求预测明年的销售额，但没说用多久的历史数据",
        must_contain=["反问", "回溯"]),

    SkillTestCase("A02", "指标未定义", [],
        "用户要求分析用户活跃度，但没定义活跃度的口径",
        must_contain=["列出", "DAU", "MAU"]),

    SkillTestCase("A03", "大范围分析", [],
        "用户要求分析过去三年的全量访问日志数据",
        must_contain=["缩小", "抽样"]),

    SkillTestCase("A04", "伪分析", [],
        "用户只给了3个数字，要求做深度分析",
        must_contain=["局限", "数据"]),

    # ══ 错误策略 ══
    SkillTestCase("A05", "超时→retry", [],
        "数据查询超时了，应该怎么处理",
        must_contain=["retry"]),

    SkillTestCase("A06", "权限→abort", [],
        "查询时遇到权限不足错误",
        must_contain=["abort"]),

    SkillTestCase("A07", "数据为空→skip", [],
        "查询返回空结果集，不是致命错误",
        must_contain=["skip"]),

    SkillTestCase("A08", "规则违规→abort", [],
        "检测到规则违规，涉及安全红线",
        must_contain=["abort"]),

    # ══ Reroute ══
    SkillTestCase("A09", "Reroute-非数据任务", [],
        "帮我写一个Python脚本来批量重命名文件",
        must_contain=["reroute", "general"]),

    SkillTestCase("A10", "Reroute-研究报告", [],
        "写一份关于云计算发展趋势的研究报告",
        must_contain=["reroute", "research"]),
]

harness = SkillTestHarness(
    "agent-scenarios", AGENT_RULES, CASES, "Agent场景处理与错误策略任务",
    '{"id":"A01","scenario":"...","action":"...","detail":"...","summary":"..."}',
    batch_size=1, timeout=180,
)

if __name__ == "__main__":
    sys.exit(harness.run())
