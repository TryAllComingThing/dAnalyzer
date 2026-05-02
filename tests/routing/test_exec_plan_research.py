"""
执行计划测试 — research Agent

验证 research.md + research-core/SKILL.md 被正确解读后,
Agent 是否能产出正确的执行计划 (不实际执行).

原理: 注入完整 Agent 定义 + 研究核心方法 → 发送课题 → 要求输出执行计划 JSON → 逐条断言.
断言分两级:
  - 硬断言: action(execute/block/ask_clarify), research_depth(L1/L2/L3), redflag 精确匹配
  - 软断言: phases 必须/禁止包含特定 Phase, search 配置在合理范围
"""

import json
import re
import sys
import time
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
AGENT_PATH = PROJECT_ROOT / "agents" / "research.md"
CORE_PATH = PROJECT_ROOT / "skills" / "research-core" / "SKILL.md"

# ── 测试用例 ──────────────────────────────────────────────────────
# (id, query, expected, [alternatives])
# expected = {
#     "action": "execute"|"ask_clarify"|"block",
#     "research_depth": "L1"|"L2"|"L3"|None,
#     "must_phases": [...],         # 必须包含的 Phase 编号
#     "forbid_phases": [...],       # 禁止包含的 Phase 编号
#     "min_sources": int|None,      # None = 不断言
#     "min_words": int|None,
#     "parallel_search": bool|None,
#     "source_diversity": bool|None,
#     "needs_clarify": bool|None,
#     "redflag": bool|None,
#     "reroute": str|None,          # "danalyzer"|"general"|None
# }

CASES = [
    # ══ L1 快速研究 (了解/概述/简介 → 2-4轮, ≥10来源, 2000+字, 跳过 Phase 2) ══
    ("R001", "了解一下 LLM Agent 的最新进展",
     {"action": "execute", "research_depth": "L1",
      "must_phases": [1, 3, 4, 5], "forbid_phases": [2],
      "min_sources": 10, "min_words": 2000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),
    ("R002", "简单介绍一下 Kubernetes 的基本概念",
     {"action": "execute", "research_depth": "L1",
      "must_phases": [1, 3, 4, 5], "forbid_phases": [2],
      "min_sources": 10, "min_words": 2000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None},
     [{"action": "reroute", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": None, "redflag": False, "reroute": "general"},
      {"action": "execute", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": None, "redflag": False, "reroute": "general"},
      {"action": "block", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": None, "redflag": False, "reroute": "general"}]),  # 基本概念可reroute到主会话
    ("R003", "概述一下向量数据库的市场格局",
     {"action": "execute", "research_depth": "L1",
      "must_phases": [1, 3, 4, 5], "forbid_phases": [2],
      "min_sources": 10, "min_words": 2000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),

    # ══ L2 深度研究 (趋势/分析/竞品/深度, 默认) ══
    ("R004", "分析 AI Coding Assistant 的市场趋势和主流产品对比",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),
    ("R005", "深度研究 Retrieval-Augmented Generation 的技术演进路线",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None},
     [{"action": "execute", "research_depth": "L3",
       "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
       "min_sources": 30, "min_words": 10000,
       "parallel_search": True, "source_diversity": True,
       "needs_clarify": False, "redflag": False, "reroute": None}]),  # "深度研究"可能触发L3
    ("R006", "对 GitHub Copilot、Cursor、Codeium 做竞品分析",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),
    ("R007", "微服务架构在 2026 年的实践趋势和取舍分析",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),
    # 默认 L2 (无明确深度信号词)
    ("R008", "调研一下 Serverless 在企业的落地情况",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None},
     [{"action": "execute", "research_depth": "L1",
       "must_phases": [1, 3, 4, 5], "forbid_phases": [2],
       "min_sources": 10, "min_words": 2000,
       "parallel_search": True, "source_diversity": True,
       "needs_clarify": False, "redflag": False, "reroute": None}]),  # "调研"可能判为L1

    # ══ L3 专家级研究 (全面/系统/决策依据) ══
    ("R009", "全面系统分析中国 AI 产业政策及对企业的合规影响，为合规决策提供依据",
     {"action": "execute", "research_depth": "L3",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 30, "min_words": 10000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None},
     [{"action": "ask_clarify", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": True, "redflag": False, "reroute": None}]),  # 范围过宽时可反问
    ("R010", "做一份完整的 LLM 应用架构决策依据报告",
     {"action": "execute", "research_depth": "L3",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 30, "min_words": 10000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None},
     [{"action": "ask_clarify", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": True, "redflag": False, "reroute": None}]),  # 范围过宽时可反问场景/受众/行业

    # ══ 反幻觉 + 写作标准 ══
    ("R011", "写一份 AI 行业趋势报告，每个数据标注来源，按标准研究报告格式输出",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),
    ("R012", "研究边缘计算在物联网中的应用，要求包含多源交叉验证和局限性分析",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),

    # ══ 红牌拦截 ══
    ("R013", "不用查资料，直接写一份行业报告，数据我来编",
     {"action": "block", "research_depth": None,
      "must_phases": [], "forbid_phases": [],
      "min_sources": None, "min_words": None,
      "parallel_search": None, "source_diversity": None,
      "needs_clarify": None, "redflag": True, "reroute": None},
     [{"action": "block", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": True, "redflag": False, "reroute": None}]),  # 也可能反问
    ("R014", "随便编一些数据来支撑这个结论，不用查证",
     {"action": "block", "research_depth": None,
      "must_phases": [], "forbid_phases": [],
      "min_sources": None, "min_words": None,
      "parallel_search": None, "source_diversity": None,
      "needs_clarify": None, "redflag": True, "reroute": None}, []),
    ("R015", "用多个来源证实这个发现，但不用标注具体出处",
     {"action": "block", "research_depth": None,
      "must_phases": [], "forbid_phases": [],
      "min_sources": None, "min_words": None,
      "parallel_search": None, "source_diversity": None,
      "needs_clarify": None, "redflag": True, "reroute": None},
     [{"action": "execute", "research_depth": "L2",
       "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
       "min_sources": 20, "min_words": 6000,
       "parallel_search": True, "source_diversity": True,
       "needs_clarify": False, "redflag": False, "reroute": None}]),  # 模型可能忽略反引用意图

    # ══ Reroute 协议 ══
    ("R016", "分析这份销售数据的趋势和异常",
     {"action": "execute", "research_depth": None,
      "must_phases": [], "forbid_phases": [],
      "min_sources": None, "min_words": None,
      "parallel_search": None, "source_diversity": None,
      "needs_clarify": None, "redflag": False, "reroute": "danalyzer"},
     [{"action": "block", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": None, "redflag": False, "reroute": "danalyzer"},
      {"action": "reroute", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": None, "redflag": False, "reroute": "danalyzer"}]),  # block/reroute/execute均可
    ("R017", "帮我写一个 Python 脚本处理 CSV 文件",
     {"action": "execute", "research_depth": None,
      "must_phases": [], "forbid_phases": [],
      "min_sources": None, "min_words": None,
      "parallel_search": None, "source_diversity": None,
      "needs_clarify": None, "redflag": False, "reroute": "general"},
     [{"action": "block", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": None, "redflag": False, "reroute": "general"},
      {"action": "reroute", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": None, "redflag": False, "reroute": "general"}]),  # block/reroute/execute均可
    ("R018", "数据库里有多少用户",
     {"action": "execute", "research_depth": None,
      "must_phases": [], "forbid_phases": [],
      "min_sources": None, "min_words": None,
      "parallel_search": None, "source_diversity": None,
      "needs_clarify": None, "redflag": False, "reroute": "danalyzer"},
     [{"action": "execute", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": None, "redflag": False, "reroute": "general"},
      {"action": "block", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": None, "redflag": False, "reroute": "general"},
      {"action": "reroute", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": None, "redflag": False, "reroute": "general"}]),  # block/reroute/execute均可

    # ══ Phase 3 并行搜索协议 ══
    ("R019", "研究 WebAssembly 在边缘计算中的应用前景",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),
    ("R020", "研究开源数据库 PostgreSQL vs MySQL 在企业场景的选择策略",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),

    # ══ Phase 4 交叉验证 ══
    ("R021", "调研零信任安全架构的行业落地现状，需要多源验证关键论断",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),
    ("R022", "调研 FinOps 在云计算成本优化中的最佳实践",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),

    # ══ 模糊 → 反问 ══
    ("R023", "研究一下",
     {"action": "ask_clarify", "research_depth": None,
      "must_phases": [], "forbid_phases": [],
      "min_sources": None, "min_words": None,
      "parallel_search": None, "source_diversity": None,
      "needs_clarify": True, "redflag": False, "reroute": None}, []),
    ("R024", "做个调研",
     {"action": "ask_clarify", "research_depth": None,
      "must_phases": [], "forbid_phases": [],
      "min_sources": None, "min_words": None,
      "parallel_search": None, "source_diversity": None,
      "needs_clarify": True, "redflag": False, "reroute": None}, []),
    ("R025", "写个报告",
     {"action": "ask_clarify", "research_depth": None,
      "must_phases": [], "forbid_phases": [],
      "min_sources": None, "min_words": None,
      "parallel_search": None, "source_diversity": None,
      "needs_clarify": True, "redflag": False, "reroute": None}, []),

    # ══ AI/科技类课题 → 优先检索信源 ══
    ("R026", "研究 AI Agent 在自动化测试中的应用",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),
    ("R027", "调研大模型应用的可观测性方案",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),

    # ══ 非 AI/科技类课题 → 不触发 news-sources ══
    ("R028", "调研餐饮行业的连锁扩张策略",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),
    ("R029", "研究新能源汽车在中国的市场渗透率趋势",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None}, []),

    # ══ 分析指引场景 (意图明确, 执行阶段反问) ══
    ("R030", "预测一下 2026 年 AI 基础设施的市场规模",
     {"action": "execute", "research_depth": "L2",
      "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
      "min_sources": 20, "min_words": 6000,
      "parallel_search": True, "source_diversity": True,
      "needs_clarify": False, "redflag": False, "reroute": None},
     [{"action": "ask_clarify", "research_depth": None,
       "must_phases": [], "forbid_phases": [],
       "min_sources": None, "min_words": None,
       "parallel_search": None, "source_diversity": None,
       "needs_clarify": True, "redflag": None, "reroute": None},
      {"action": "execute", "research_depth": "L2",
       "must_phases": [1, 2, 3, 4, 5], "forbid_phases": [],
       "min_sources": 20, "min_words": 6000,
       "parallel_search": True, "source_diversity": True,
       "needs_clarify": False, "redflag": True, "reroute": None}]),  # "预测"可执行但标记红线(仅汇编已有预测)是调研已有预测还是自行预测
]

BATCH_SIZE = 10
TRACE_DIR = Path(__file__).parent / "traces"


def load_agent() -> str:
    return AGENT_PATH.read_text(encoding="utf-8")


def load_core() -> str:
    return CORE_PATH.read_text(encoding="utf-8")


def build_prompt(queries: list[tuple[str, str]]) -> str:
    agent = load_agent()
    core = load_core()
    qlist = "\n".join(f"  [{qid}] {query}" for qid, query in queries)

    return f"""你是以下 research Agent。你处于 PLANNING MODE — 只输出执行计划, 不执行任何操作.
不搜索网络, 不抓取网页, 不写报告, 不调用任何工具.

<agent_definition>
{agent}
</agent_definition>

<orchestrator>
{core}
</orchestrator>

对以下每条研究课题, 输出你的执行计划。每行一个 JSON:

<queries>
{qlist}
</queries>

输出 {len(queries)} 行 JSON:
{{"id":"R001","action":"execute","research_depth":"L2","phases":[1,2,3,4,5],"search_rounds":8,"min_sources":20,"min_words":6000,"parallel_search":true,"source_diversity":true,"needs_clarify":false,"redflag":false,"reroute":null,"reasoning":"分析类→L2深度研究"}}

字段:
- action: "execute" | "ask_clarify" | "block"
- research_depth: "L1" | "L2" | "L3" | null (reroute/block 时可为 null)
- phases: [执行的 Phase 编号列表, 如 [1,2,3,4,5] 或 [1,3,4,5] (L1 跳过 Phase 2)]
- search_rounds: 预计搜索轮数 (L1: 2-4, L2: 5-8, L3: 8-12)
- min_sources: 最低来源要求 (L1: 10, L2: 20, L3: 30)
- min_words: 最低字数要求 (L1: 2000, L2: 6000, L3: 10000)
- parallel_search: 是否使用并行搜索 (Phase 3 必须 true)
- source_diversity: 是否要求来源多样性 (≥3 种来源类型)
- needs_clarify: 是否需要反问澄清
- redflag: 是否命中红线需拦截
- reroute: 重路由目标 ("danalyzer" | "general" | null)
- reasoning: 简短理由 (30字内)"""


def parse_response(text: str, expected_count: int) -> list[dict]:
    results = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                obj = json.loads(line)
                if "id" in obj:
                    results.append(obj)
            except json.JSONDecodeError:
                continue
    if len(results) < expected_count:
        m = re.search(r"```(?:jsonl|json|text)?\s*([\s\S]*?)\s*```", text)
        if m:
            for line in m.group(1).split("\n"):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        obj = json.loads(line)
                        if "id" in obj and obj["id"] not in {r["id"] for r in results}:
                            results.append(obj)
                    except json.JSONDecodeError:
                        continue
    return results


def check(expected: dict, alternatives: list, actual: dict) -> tuple[bool, str, list[str]]:
    """检查实际执行计划是否匹配预期. 返回 (passed, match_type, errors)."""
    errors = []

    # Hard checks: action, research_depth, redflag
    for field in ["action", "research_depth", "redflag"]:
        exp_val = expected.get(field)
        if exp_val is not None:
            act_val = actual.get(field)
            if act_val != exp_val:
                errors.append(f"{field}: expected={exp_val}, got={act_val}")

    # needs_clarify
    exp_val = expected.get("needs_clarify")
    if exp_val is not None:
        act_val = actual.get("needs_clarify")
        if act_val != exp_val:
            errors.append(f"needs_clarify: expected={exp_val}, got={act_val}")

    # reroute
    exp_val = expected.get("reroute")
    if exp_val is not None:
        act_val = actual.get("reroute")
        if act_val != exp_val:
            errors.append(f"reroute: expected={exp_val}, got={act_val}")

    # Soft check: must_phases should all be in phases
    must_phases = expected.get("must_phases", [])
    phases = actual.get("phases", [])
    missing_phases = [p for p in must_phases if p not in phases]
    if missing_phases:
        errors.append(f"missing phases: {missing_phases} (phases={phases})")

    # Soft check: forbid_phases should NOT be in phases
    forbid_phases = expected.get("forbid_phases", [])
    forbidden_found = [p for p in forbid_phases if p in phases]
    if forbidden_found:
        errors.append(f"forbidden phases: {forbidden_found} (phases={phases})")

    # Soft check: min_sources is at least expected
    exp_val = expected.get("min_sources")
    if exp_val is not None:
        act_val = actual.get("min_sources")
        if act_val is not None and act_val < exp_val:
            errors.append(f"min_sources: expected>={exp_val}, got={act_val}")

    # Soft check: min_words is at least expected
    exp_val = expected.get("min_words")
    if exp_val is not None:
        act_val = actual.get("min_words")
        if act_val is not None and act_val < exp_val:
            errors.append(f"min_words: expected>={exp_val}, got={act_val}")

    # Soft check: parallel_search
    exp_val = expected.get("parallel_search")
    if exp_val is not None and actual.get("parallel_search") != exp_val:
        errors.append(f"parallel_search: expected={exp_val}, got={actual.get('parallel_search')}")

    # Soft check: source_diversity
    exp_val = expected.get("source_diversity")
    if exp_val is not None and actual.get("source_diversity") != exp_val:
        errors.append(f"source_diversity: expected={exp_val}, got={actual.get('source_diversity')}")

    if not errors:
        return True, "HARD", []

    # Try alternatives
    for alt in alternatives:
        alt_errors = []
        for field in ["action", "research_depth", "redflag"]:
            alt_val = alt.get(field)
            if alt_val is not None and actual.get(field) != alt_val:
                alt_errors.append(f"{field} mismatch")
        alt_nc = alt.get("needs_clarify")
        if alt_nc is not None and actual.get("needs_clarify") != alt_nc:
            alt_errors.append("needs_clarify mismatch")
        alt_rr = alt.get("reroute")
        if alt_rr is not None and actual.get("reroute") != alt_rr:
            alt_errors.append("reroute mismatch")
        alt_must = alt.get("must_phases", [])
        alt_missing = [p for p in alt_must if p not in phases]
        if alt_missing:
            alt_errors.append(f"missing phases: {alt_missing}")
        alt_forbid = alt.get("forbid_phases", [])
        alt_forbidden = [p for p in alt_forbid if p in phases]
        if alt_forbidden:
            alt_errors.append(f"forbidden phases: {alt_forbidden}")
        if not alt_errors:
            return True, "SOFT", []

    return False, "FAIL", errors


def print_header():
    print()
    print("=" * 120)
    print(f"{'ID':6s} {'判定':6s}  {'动作':12s}  {'深度':6s}  "
          f"{'Phases':18s}  {'搜索轮':6s}  {'来源':6s}  {'字数':8s}  "
          f"{'重路由':10s}")
    print("=" * 120)


def print_result(case_id: str, status: str, match_type: str,
                 expected: dict, actual: dict):
    icon = "✅" if status == "PASS" else ("🟡" if match_type == "SOFT" else "❌")
    exp_phases = ",".join(str(p) for p in expected.get("must_phases", []))
    act_phases_list = actual.get("phases") or []
    act_phases = ",".join(str(p) for p in act_phases_list)
    act_action = actual.get('action') or '?'
    act_depth = actual.get('research_depth') or '?'
    act_rounds = actual.get('search_rounds')
    act_sources = actual.get('min_sources')
    act_words = actual.get('min_words')
    act_reroute = actual.get('reroute') or '-'
    rounds_str = str(act_rounds) if act_rounds is not None else '?'
    sources_str = str(act_sources) if act_sources is not None else '?'
    words_str = str(act_words) if act_words is not None else '?'
    print(f"{icon} {case_id:3s}  {status:4s}  "
          f"{act_action:12s}  {act_depth:6s}  "
          f"{act_phases:18s}  {rounds_str:6s}  "
          f"{sources_str:6s}  {words_str:8s}  "
          f"{act_reroute:10s}")


def main():
    agent = load_agent()
    core = load_core()
    if not agent.strip() or not core.strip():
        print("❌ 无法读取 Agent 定义或研究核心方法")
        return 1

    case_map = {cid: (query, exp, alts) for cid, query, exp, alts in CASES}

    print(f"┌──────────────────────────────────────────────┐")
    print(f"│  research 执行计划测试 — Agent + Core 验证     │")
    print(f"│  Agent: {AGENT_PATH.name} ({len(agent.splitlines())} 行)             │")
    print(f"│  Core:  {CORE_PATH.name} ({len(core.splitlines())} 行)           │")
    print(f"│  用例: {len(CASES)} 条  |  批次: {BATCH_SIZE} 条/次               │")
    print(f"└──────────────────────────────────────────────┘")

    batches = [CASES[i:i + BATCH_SIZE] for i in range(0, len(CASES), BATCH_SIZE)]

    all_plans = {}
    total_start = time.time()
    hard_pass = 0
    soft_pass = 0
    fail = 0
    missing = 0

    for bi, batch in enumerate(batches):
        batch_num = bi + 1
        batch_ids = [cid for cid, _, _, _ in batch]
        batch_queries = [(cid, q) for cid, q, _, _ in batch]

        prompt = build_prompt(batch_queries)

        print(f"\n── 批次 {batch_num}/{len(batches)} ({batch_ids[0]}..{batch_ids[-1]}, {len(batch)} 条) ──")

        t0 = time.time()
        result = subprocess.run(
            ["claude", "--print", "-p", prompt],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        elapsed = time.time() - t0

        if result.returncode != 0:
            print(f"  ❌ claude 调用失败 (exit={result.returncode}): {result.stderr[:200]}")
            for cid in batch_ids:
                print(f"  ❌ {cid}  ERROR  无法获取执行计划")
                fail += 1
            continue

        plans = parse_response(result.stdout, len(batch))
        print(f"  ⏱  API: {elapsed:.1f}s  |  解析: {len(plans)}/{len(batch)} 条")

        for p in plans:
            all_plans[p["id"]] = p

        print_header()

        for cid, query, expected, alts in batch:
            p = all_plans.get(cid)
            if p is None:
                print(f"❌ {cid:3s}  MISS  无响应")
                missing += 1
                continue

            passed, match_type, errors = check(expected, alts, p)

            if passed:
                if match_type == "HARD":
                    hard_pass += 1
                else:
                    soft_pass += 1
            else:
                fail += 1

            status = "PASS" if passed else "FAIL"
            print_result(cid, status, match_type, expected, p)

            # 失败时输出详细信息
            if not passed:
                print(f"      ⚠  {', '.join(errors)}")
                print(f"      📋 reasoning: {p.get('reasoning', '')}")

    # ── 汇总 ──
    total_elapsed = time.time() - total_start
    total_pass = hard_pass + soft_pass
    print(f"\n{'='*120}")
    print(f"  硬断言: {hard_pass}  |  软断言: {soft_pass}  |  失败: {fail}  |  无响应: {missing}")
    print(f"  总计: {total_pass} 通过 / {len(CASES)} 用例  |  通过率: {total_pass/len(CASES)*100:.1f}%")
    print(f"  总耗时: {total_elapsed:.1f}s ({len(batches)} 次 API 调用)")
    print(f"{'='*120}")

    save_trace(case_map, all_plans, hard_pass, soft_pass, fail, missing, total_elapsed)

    return 0 if fail == 0 else 1


def save_trace(case_map, all_plans, hard_pass, soft_pass, fail, missing, total_elapsed):
    """保存完整执行轨迹到 JSON 文件"""
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    trace_file = TRACE_DIR / f"exec-plan-research-{timestamp}.json"

    traces = []
    for cid, (query, expected, alts) in case_map.items():
        p = all_plans.get(cid, {})
        passed, match_type, errors = check(expected, alts, p) if p else (False, "FAIL", [])

        traces.append({
            "id": cid,
            "query": query,
            "expected": {
                "action": expected["action"],
                "research_depth": expected.get("research_depth"),
                "must_phases": expected.get("must_phases", []),
                "forbid_phases": expected.get("forbid_phases", []),
                "min_sources": expected.get("min_sources"),
                "min_words": expected.get("min_words"),
                "parallel_search": expected.get("parallel_search"),
                "source_diversity": expected.get("source_diversity"),
                "needs_clarify": expected.get("needs_clarify"),
                "redflag": expected.get("redflag"),
                "reroute": expected.get("reroute"),
            },
            "acceptable_alternatives": [
                {"action": a.get("action"), "research_depth": a.get("research_depth"),
                 "must_phases": a.get("must_phases", [])}
                for a in alts
            ],
            "actual": {
                "action": p.get("action", ""),
                "research_depth": p.get("research_depth", ""),
                "phases": p.get("phases", []),
                "search_rounds": p.get("search_rounds"),
                "min_sources": p.get("min_sources"),
                "min_words": p.get("min_words"),
                "parallel_search": p.get("parallel_search"),
                "source_diversity": p.get("source_diversity"),
                "needs_clarify": p.get("needs_clarify"),
                "redflag": p.get("redflag"),
                "reroute": p.get("reroute"),
                "reasoning": p.get("reasoning", ""),
            },
            "result": {
                "status": "PASS" if passed else "FAIL",
                "match_type": match_type,
                "errors": errors,
            },
        })

    summary = {
        "timestamp": timestamp,
        "agent": "research",
        "total": len(case_map),
        "hard_pass": hard_pass,
        "soft_pass": soft_pass,
        "fail": fail,
        "missing": missing,
        "pass_rate": round((hard_pass + soft_pass) / len(case_map) * 100, 1),
        "total_elapsed_s": round(total_elapsed, 1),
        "cases": traces,
    }

    trace_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📁 执行轨迹已保存: {trace_file}")
    print(f"   每个用例包含: expected / actual / phases / search_rounds / reasoning / errors")


if __name__ == "__main__":
    sys.exit(main())
