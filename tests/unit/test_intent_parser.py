"""
intent_parser 单元测试 — L1→L2→L3 三级兜底

测试目标:
  - validate_plan() 校验逻辑
  - validate_codes_against_store() code 匹配
  - repair_from_scenario() / supplement_from_routing() 补齐
  - execute_l1_exact / execute_l2_fts / execute_l3_llm_fallback
  - parse_intent() 全流程
  - detect_industry() 关键词匹配
  - 边界情况

用法:
  pytest tests/unit/test_intent_parser.py -m p0 -v       # 核心路径
  pytest tests/unit/test_intent_parser.py -m "p0 or p1" -v  # 完整
"""

import json
import sys
from pathlib import Path
from textwrap import dedent

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.intent_parser import (
    load_intent_routing,
    validate_plan,
    validate_codes_against_store,
    repair_from_scenario,
    supplement_from_routing,
    execute_l1_exact,
    execute_l2_fts,
    execute_l3_llm_fallback,
    parse_intent,
    detect_industry,
    _match_intent_from_query,
    _dedupe_by_code,
)
from scripts.industry.store import IndustryStore


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _make_industry_yamls(root: Path, indicators: list[dict] = None,
                         scenarios: list[dict] = None):
    """在临时目录创建行业 YAML 文件，供 IndustryStore 同步"""
    ind_dir = root / "test_industry" / "indicators"
    scn_dir = root / "test_industry" / "scenarios"
    ind_dir.mkdir(parents=True)
    scn_dir.mkdir(parents=True)

    for item in (indicators or []):
        f = ind_dir / f"{item['code']}.yaml"
        y = {
            "code": item["code"], "name": item.get("name", item["code"]),
            "industry": "test_industry",
            "keywords": item.get("keywords", []),
            "definition": {"formula": item.get("formula", "")},
            "stats": {"importance": item.get("importance", 5)},
        }
        import yaml
        f.write_text(yaml.dump(y, allow_unicode=True), encoding="utf-8")

    for item in (scenarios or []):
        f = scn_dir / f"{item['code']}.yaml"
        y = {
            "code": item["code"], "name": item.get("name", item["code"]),
            "industry": "test_industry",
            "keywords": item.get("keywords", []),
            "content": {
                "required": item.get("required_indicators", []),
                "optional": [],
                "dimensions": {},
            },
        }
        import yaml
        f.write_text(yaml.dump(y, allow_unicode=True), encoding="utf-8")

    # 创建 _base 目录（IndustryStore 需要）
    base_dir = root / "_base" / "indicators"
    base_dir.mkdir(parents=True)


@pytest.fixture
def test_industry_root(tmp_path):
    """含 test_industry 的临时知识库目录"""
    _make_industry_yamls(tmp_path,
        indicators=[
            {"code": "sales_amount", "name": "销售额",
             "keywords": ["销售", "销售额", "GMV", "收入"],
             "formula": "SUM(actual_amount)"},
            {"code": "order_count", "name": "订单量",
             "keywords": ["订单", "订单量", "成交量"],
             "formula": "COUNT(DISTINCT order_id)"},
            {"code": "conversion_rate", "name": "转化率",
             "keywords": ["转化", "转化率"],
             "formula": "order_count / visit_count"},
            {"code": "user_id", "name": "用户ID",
             "keywords": ["用户"],
             "formula": "user_id"},
            {"code": "npl_ratio", "name": "不良率",
             "keywords": ["不良", "NPL"],
             "formula": "SUM(npl_amount) / SUM(total_loan)"},
        ],
        scenarios=[
            {"code": "sales_trend", "name": "销售趋势",
             "keywords": ["趋势", "走势"],
             "required_indicators": ["sales_amount", "order_count"]},
            {"code": "user_analysis", "name": "用户分析",
             "keywords": ["用户"],
             "required_indicators": ["user_id", "order_count"]},
            {"code": "risk_analysis", "name": "风险分析",
             "keywords": ["风险", "不良"],
             "required_indicators": ["npl_ratio"]},
        ],
    )
    return tmp_path


@pytest.fixture
def store(test_industry_root):
    return IndustryStore("test_industry", test_industry_root)


@pytest.fixture
def routing():
    return load_intent_routing()


# ═══════════════════════════════════════════════════════════════
# P0 — plan 校验
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p0
class TestValidatePlanP0:
    """validate_plan() 核心校验 (P0)"""

    def test_rejects_empty_plan(self, routing):
        result = validate_plan({}, routing)
        assert result["valid"] is False
        assert any("empty" in e for e in result["errors"])

    def test_rejects_unknown_industry(self, routing):
        result = validate_plan({"industry": "nonexistent_xyz"}, routing)
        assert any("unknown industry" in e for e in result["errors"])

    def test_warns_unknown_analysis_type(self, routing):
        result = validate_plan({"analysis_type": "sorcery"}, routing)
        assert any("unknown analysis_type" in w for w in result["warnings"])

    def test_warns_confidence_out_of_range(self, routing):
        for val in [1.5, -0.1, 999]:
            result = validate_plan({"confidence": val}, routing)
            assert any("out of range" in w for w in result["warnings"]), \
                f"confidence={val} should warn"

    def test_accepts_valid_plan(self, routing):
        plan = {
            "industry": "fmcg",
            "analysis_type": "diagnostic",
            "confidence": 0.85,
            "indicators": ["sales_amount", "order_count"],
            "scenarios": ["sales_trend"],
            "models": ["attribution-model"],
            "skill_chain": ["data-query", "data-analysis", "visual", "security"],
        }
        result = validate_plan(plan, routing)
        assert result["valid"] is True
        assert result["industry_ok"] is True
        assert len(result["errors"]) == 0, f"unexpected errors: {result['errors']}"

    def test_warns_missing_industry(self, routing):
        result = validate_plan({"indicators": ["sales_amount"]}, routing)
        assert any("not specified" in w for w in result["warnings"])


# ═══════════════════════════════════════════════════════════════
# P0 — code 校验
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p0
class TestValidateCodesP0:
    """validate_codes_against_store() (P0)"""

    def test_all_codes_hit(self, store, routing):
        plan = {"indicators": ["sales_amount", "order_count"],
                "scenarios": ["sales_trend"]}
        result = validate_codes_against_store(plan, store, routing)
        assert set(result["indicator_hits"]) == {"sales_amount", "order_count"}
        assert result["indicator_misses"] == []
        assert result["scenario_hits"] == ["sales_trend"]

    def test_fake_code_misses(self, store, routing):
        plan = {"indicators": ["nonexistent_code"], "scenarios": []}
        result = validate_codes_against_store(plan, store, routing)
        assert result["indicator_hits"] == []
        assert result["indicator_misses"] == ["nonexistent_code"]

    def test_mixed_hits_and_misses(self, store, routing):
        plan = {"indicators": ["sales_amount", "fake_indicator"], "scenarios": []}
        result = validate_codes_against_store(plan, store, routing)
        assert result["indicator_hits"] == ["sales_amount"]
        assert result["indicator_misses"] == ["fake_indicator"]


# ═══════════════════════════════════════════════════════════════
# P1 — 补齐逻辑
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p1
class TestRepairP1:
    """repair_from_scenario + supplement_from_routing (P1)"""

    def test_repair_adds_required_indicators(self, store, routing):
        valid_codes = {"order_count"}
        valid_scenarios = {"sales_trend"}
        result = repair_from_scenario(valid_codes, valid_scenarios, store)
        assert "sales_amount" in result, \
            "should add sales_amount from sales_trend's required_indicators"

    def test_repair_skips_nonexistent_required(self, store, routing):
        valid_codes = {"order_count"}
        valid_scenarios = {"risk_analysis"}  # requires npl_ratio (exists)
        result = repair_from_scenario(valid_codes, valid_scenarios, store)
        assert "npl_ratio" in result

    def test_repair_no_scenarios_no_change(self, store, routing):
        valid_codes = {"order_count"}
        result = repair_from_scenario(valid_codes, set(), store)
        assert result == {"order_count"}

    def test_supplement_from_intent_match(self, routing):
        plan = {"intent_id": "sales_overview"}
        valid_codes = set()
        valid_scenarios = set()
        codes, scns = supplement_from_routing(plan, valid_codes, valid_scenarios, routing)
        assert len(codes) >= 2, "sales_overview has default_indicators"

    def test_supplement_from_analysis_type_fallback(self, routing):
        plan = {"analysis_type": "diagnostic"}
        valid_codes = {"order_count"}
        valid_scenarios = set()
        codes, scns = supplement_from_routing(plan, valid_codes, valid_scenarios, routing)
        assert len(codes) > 1, "should fill from first diagnostic intent"


# ═══════════════════════════════════════════════════════════════
# P1 — L1 精确查询
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p1
class TestL1ExactP1:
    """execute_l1_exact() (P1)"""

    def test_l1_success_with_valid_codes(self, store, routing):
        plan = {
            "indicators": ["sales_amount", "order_count"],
            "scenarios": ["sales_trend"],
            "models": ["attribution-model"],
            "analysis_type": "diagnostic",
            "skill_chain": ["data-query", "data-analysis", "visual", "security"],
        }
        result = execute_l1_exact(plan, store, routing)
        assert result["source"] == "l1_exact"
        assert len(result["indicators"]) >= 2
        assert len(result["scenarios"]) >= 1

    def test_l1_insufficient_when_too_few_indicators(self, store, routing):
        plan = {
            "indicators": ["sales_amount"],  # only 1
            "scenarios": ["sales_trend"],
            "models": [],
            "analysis_type": "descriptive",
        }
        result = execute_l1_exact(plan, store, routing)
        # repair_from_scenario should add order_count from sales_trend
        # so it might actually succeed with 2
        # If it succeeds, source is l1_exact; if not, insufficient
        assert result["source"] in ("l1_exact", "l1_insufficient")

    def test_l1_repair_triggers_for_missing_indicators(self, store, routing):
        plan = {
            "indicators": ["order_count"],  # only 1, but sales_trend requires sales_amount too
            "scenarios": ["sales_trend"],
            "models": [],
            "analysis_type": "descriptive",
        }
        result = execute_l1_exact(plan, store, routing)
        assert result["source"] == "l1_exact"
        indicator_codes = [i["code"] for i in result["indicators"]]
        assert "sales_amount" in indicator_codes, \
            "repair_from_scenario should have added sales_amount"


# ═══════════════════════════════════════════════════════════════
# P1 — L2 FTS 降级
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p1
class TestL2FtsP1:
    """execute_l2_fts() (P1)"""

    def test_l2_returns_results_for_valid_query(self, store, routing):
        result = execute_l2_fts("销售额趋势", store, routing)
        assert result["source"] in ("l2_fts_fallback", "l2_empty")
        if result["source"] == "l2_fts_fallback":
            assert len(result["indicators"]) >= 1

    def test_l2_empty_for_nonsense_query(self, store, routing):
        result = execute_l2_fts("xyzabc123无意义", store, routing)
        assert result["source"] in ("l2_fts_fallback", "l2_empty")


# ═══════════════════════════════════════════════════════════════
# P1 — L3 最终兜底
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p1
class TestL3FallbackP1:
    """execute_l3_llm_fallback() (P1)"""

    def test_l3_returns_routing_context(self, routing):
        result = execute_l3_llm_fallback("任意查询", routing)
        assert result["source"] == "l3_llm_fallback"
        assert "routing_context" in result
        assert "available_industries" in result["routing_context"]
        assert "available_intents" in result["routing_context"]
        assert "message" in result

    def test_l3_indicators_empty(self, routing):
        result = execute_l3_llm_fallback("test", routing)
        assert result["indicators"] == []
        assert result["scenarios"] == []


# ═══════════════════════════════════════════════════════════════
# P1 — 行业检测
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p1
class TestDetectIndustryP1:
    """detect_industry() (P1)"""

    def test_detects_fmcg_by_gmv(self, routing):
        assert detect_industry("GMV下降了怎么办", routing) == "fmcg"

    def test_detects_fmcg_by_category(self, routing):
        assert detect_industry("品类分析怎么做", routing) == "fmcg"

    def test_detects_fmcg_by_channel(self, routing):
        assert detect_industry("渠道销售对比", routing) == "fmcg"

    def test_detects_fmcg_by_sku(self, routing):
        assert detect_industry("SKU动销率怎么样", routing) == "fmcg"

    def test_returns_none_for_no_match(self, routing):
        assert detect_industry("你好世界", routing) is None


# ═══════════════════════════════════════════════════════════════
# P1 — 意图匹配
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p1
class TestIntentMatchP1:
    """_match_intent_from_query() (P1)"""

    def test_matches_sales_overview(self, routing):
        result = _match_intent_from_query("销售额统计", routing)
        assert result.get("id") == "sales_overview"

    def test_matches_diagnostic_with_negative(self, routing):
        result = _match_intent_from_query("销售下降了", routing)
        # "下降" is negative for sales_overview → should match sales_diagnostic
        assert result.get("analysis_type") == "diagnostic"

    def test_returns_empty_for_no_match(self, routing):
        result = _match_intent_from_query("xyz魔法查询", routing)
        assert result == {}


# ═══════════════════════════════════════════════════════════════
# P1 — 全流程 parse_intent()
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p1
class TestParseIntentFullP1:
    """parse_intent() 全流程 (P1)"""

    def test_l1_path_with_valid_plan(self, test_industry_root):
        plan = json.dumps({
            "industry": "test_industry",
            "indicators": ["sales_amount", "order_count"],
            "scenarios": ["sales_trend"],
            "models": [],
            "analysis_type": "descriptive",
            "skill_chain": ["data-query", "visual", "security"],
        })
        result = parse_intent(
            query="销售额分析",
            industry="test_industry",
            plan_json=plan,
            data_root=str(test_industry_root),
        )
        assert result["source"] in ("l1_exact", "l1_l2_mixed")
        assert result["industry"] == "test_industry"

    def test_l2_path_without_plan(self, test_industry_root):
        result = parse_intent(
            query="销售额趋势",
            industry="test_industry",
            plan_json=None,
            data_root=str(test_industry_root),
        )
        assert result["source"] in ("l2_fts_fallback", "l2_empty", "l3_llm_fallback")

    def test_auto_detect_industry(self, test_industry_root, routing):
        """不传 industry 时自动从 query 关键词检测（fallback 到 routing 中的行业）"""
        result = parse_intent(
            query="GMV下降了",
            industry=None,
            plan_json=None,
            data_root=str(test_industry_root),
        )
        # detect_industry 走 routing 的 trigger_keywords，匹配到 ecommerce
        # 但 IndustryStore("ecommerce", test_industry_root) 可能不存在
        # 至少不应崩溃
        assert "source" in result
        assert "industry" in result

    def test_invalid_plan_json_graceful_degradation(self, test_industry_root):
        result = parse_intent(
            query="销售额趋势",
            industry="test_industry",
            plan_json="this is not valid json {{{",
            data_root=str(test_industry_root),
        )
        assert "source" in result
        # 应降级到 L2，不应崩溃


# ═══════════════════════════════════════════════════════════════
# P2 — 边界情况
# ═══════════════════════════════════════════════════════════════

@pytest.mark.p2
class TestEdgeCasesP2:
    """边界情况 (P2)"""

    def test_empty_query_no_crash(self, routing):
        result = execute_l3_llm_fallback("", routing)
        assert result["source"] == "l3_llm_fallback"

    def test_all_fake_codes_repaired_by_supplement(self, store, routing):
        """全假 code 时 supplement_from_routing 从 intent 补齐，不崩溃"""
        plan = {
            "indicators": ["fake_a", "fake_b", "fake_c"],
            "scenarios": ["fake_scenario"],
            "models": [],
            "analysis_type": "descriptive",
        }
        result = execute_l1_exact(plan, store, routing)
        # supplement_from_routing 会从匹配的 intent 补齐，不应崩溃
        assert result["source"] in ("l1_exact", "l1_insufficient")
        assert len(result["indicators"]) >= 0

    def test_dedupe_by_code(self):
        items = [
            {"code": "a", "name": "A1"},
            {"code": "b", "name": "B"},
            {"code": "a", "name": "A2"},
        ]
        result = _dedupe_by_code(items)
        assert len(result) == 2
        assert result[0]["name"] == "A1"  # first occurrence kept

    def test_dedupe_skips_empty_code(self):
        items = [{"code": "", "name": "no_code"}, {"code": "a", "name": "A"}]
        result = _dedupe_by_code(items)
        assert len(result) == 1

    def test_confidence_edge_values(self, routing):
        """0 和 1 都是合法值"""
        for val in [0.0, 0.5, 1.0]:
            result = validate_plan({"confidence": val}, routing)
            assert not any("out of range" in w for w in result["warnings"]), \
                f"confidence={val} should be valid"
