"""
知识库数据完整性校验 — 验证 knowledge/industry/fmcg/ YAML schema 和交叉引用

测试层级:
  P0: Indicator/Scenario schema + 交叉引用完整性
  P1: 数据一致性 (orphan 检测 / formula 引用 / skill 链)
  P2: 数据质量 (importance 分布 / 更新日期)

用法:
  pytest tests/unit/test_knowledge_integrity.py -m p0 -v    # 核心路径
  pytest tests/unit/test_knowledge_integrity.py -v            # 全部
"""

import re
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
FMCG_DIR = PROJECT_ROOT / "knowledge" / "industry" / "fmcg"
INDICATORS_DIR = FMCG_DIR / "indicators"
SCENARIOS_DIR = FMCG_DIR / "scenarios"
INTENT_ROUTING_PATH = PROJECT_ROOT / "knowledge" / "intent-routing.yaml"
MODELS_DIR = PROJECT_ROOT / "knowledge" / "model"
SKILLS_DIR = PROJECT_ROOT / "skills"

# SQL/公式中应忽略的函数和关键字
SQL_KEYWORDS = {
    "SUM", "COUNT", "AVG", "MAX", "MIN", "DISTINCT", "GROUP", "BY",
    "ORDER", "WHERE", "AND", "OR", "NOT", "NULL", "AS", "ON", "IN",
    "BETWEEN", "LIKE", "HAVING", "LIMIT", "OFFSET", "CASE", "WHEN",
    "THEN", "ELSE", "END", "COALESCE", "IF", "CAST", "CONVERT",
    "SQRT", "ABS", "ROUND", "CEIL", "FLOOR", "POWER", "LOG", "EXP",
    "DATE", "DATE_FORMAT", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE",
    "LEFT", "RIGHT", "INNER", "JOIN", "OUTER", "FULL", "CROSS",
    "UNION", "ALL", "SELECT", "FROM", "WITH", "OVER", "PARTITION",
}


def _load_yaml(path: Path) -> dict | None:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_all_indicators() -> dict[str, dict]:
    result = {}
    if not INDICATORS_DIR.exists():
        return result
    for f in sorted(INDICATORS_DIR.glob("*.yaml")):
        data = _load_yaml(f)
        if data and "code" in data:
            result[data["code"]] = data
    return result


def _load_all_scenarios() -> dict[str, dict]:
    result = {}
    if not SCENARIOS_DIR.exists():
        return result
    for f in sorted(SCENARIOS_DIR.glob("*.yaml")):
        data = _load_yaml(f)
        if data and "code" in data:
            result[data["code"]] = data
    return result


def _load_intent_routing() -> dict | None:
    return _load_yaml(INTENT_ROUTING_PATH)


def _get_existing_skills() -> set[str]:
    if not SKILLS_DIR.exists():
        return set()
    return {d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")}


# ═══════════════════════════════════════════════════════════════
# P0 — Indicator Schema 校验
# ═══════════════════════════════════════════════════════════════


@pytest.mark.p0
class TestIndicatorSchemaValidation:
    """验证所有指标 YAML 的 schema 完整性"""

    INDICATOR_REQUIRED_TOP = {"code", "name", "industry", "keywords", "description"}
    INDICATOR_REQUIRED_DEF = {"formula", "unit", "precision"}
    INDICATOR_REQUIRED_STATS = {"importance", "updated"}

    @pytest.fixture(scope="class")
    def indicators(self):
        return _load_all_indicators()

    def test_indicators_exist(self, indicators):
        assert len(indicators) >= 30, f"指标数量过少: {len(indicators)}"

    @pytest.mark.parametrize("code", list(_load_all_indicators().keys()))
    def test_has_required_top_fields(self, code):
        data = _load_all_indicators()[code]
        missing = self.INDICATOR_REQUIRED_TOP - set(data.keys())
        assert not missing, f"{code}: 缺少字段: {missing}"

    @pytest.mark.parametrize("code", list(_load_all_indicators().keys()))
    def test_definition_has_required_fields(self, code):
        data = _load_all_indicators()[code]
        definition = data.get("definition", {})
        missing = self.INDICATOR_REQUIRED_DEF - set(definition.keys())
        assert not missing, f"{code}: definition 缺少字段: {missing}"

    @pytest.mark.parametrize("code", list(_load_all_indicators().keys()))
    def test_stats_has_required_fields(self, code):
        data = _load_all_indicators()[code]
        stats = data.get("stats", {})
        missing = self.INDICATOR_REQUIRED_STATS - set(stats.keys())
        assert not missing, f"{code}: stats 缺少字段: {missing}"

    @pytest.mark.parametrize("code", list(_load_all_indicators().keys()))
    def test_importance_in_range(self, code):
        data = _load_all_indicators()[code]
        importance = data.get("stats", {}).get("importance", -1)
        assert 0.0 <= importance <= 1.0, \
            f"{code}: importance={importance} 不在 [0.0, 1.0] 范围"

    @pytest.mark.parametrize("code", list(_load_all_indicators().keys()))
    def test_precision_is_nonnegative_int(self, code):
        data = _load_all_indicators()[code]
        precision = data.get("definition", {}).get("precision", -1)
        assert isinstance(precision, int), \
            f"{code}: precision 应为 int, 实际 {type(precision).__name__}"
        assert precision >= 0, f"{code}: precision={precision} < 0"

    @pytest.mark.parametrize("code", list(_load_all_indicators().keys()))
    def test_keywords_nonempty_list(self, code):
        data = _load_all_indicators()[code]
        keywords = data.get("keywords", [])
        assert isinstance(keywords, list), f"{code}: keywords 不是 list"
        assert len(keywords) >= 1, f"{code}: keywords 为空"

    def test_filename_matches_code(self):
        for f in INDICATORS_DIR.glob("*.yaml"):
            data = _load_yaml(f)
            if not data:
                continue
            expected = f.stem
            actual = data.get("code", "")
            assert actual == expected, \
                f"{f.name}: code='{actual}' != 文件名 '{expected}'"

    def test_all_industry_is_fmcg(self):
        for f in INDICATORS_DIR.glob("*.yaml"):
            data = _load_yaml(f)
            if not data:
                continue
            assert data.get("industry") == "fmcg", \
                f"{f.name}: industry={data.get('industry')} != 'fmcg'"


# ═══════════════════════════════════════════════════════════════
# P0 — Scenario Schema 校验
# ═══════════════════════════════════════════════════════════════


@pytest.mark.p0
class TestScenarioSchemaValidation:
    """验证所有场景 YAML 的 schema 完整性"""

    SCENARIO_REQUIRED_TOP = {"code", "name", "industry", "keywords", "description", "content"}
    SCENARIO_REQUIRED_CONTENT = {"required", "optional", "dimensions"}
    SCENARIO_REQUIRED_STATS = {"usage_count", "satisfaction", "updated"}

    @pytest.fixture(scope="class")
    def scenarios(self):
        return _load_all_scenarios()

    def test_scenarios_exist(self, scenarios):
        assert len(scenarios) >= 10, f"场景数量过少: {len(scenarios)}"

    @pytest.mark.parametrize("code", list(_load_all_scenarios().keys()))
    def test_has_required_top_fields(self, code):
        data = _load_all_scenarios()[code]
        missing = self.SCENARIO_REQUIRED_TOP - set(data.keys())
        assert not missing, f"{code}: 缺少字段: {missing}"

    @pytest.mark.parametrize("code", list(_load_all_scenarios().keys()))
    def test_content_has_required_fields(self, code):
        data = _load_all_scenarios()[code]
        content = data.get("content", {})
        missing = self.SCENARIO_REQUIRED_CONTENT - set(content.keys())
        assert not missing, f"{code}: content 缺少字段: {missing}"
        assert isinstance(content.get("required"), list), f"{code}: required 应为 list"
        assert isinstance(content.get("optional"), list), f"{code}: optional 应为 list"
        assert isinstance(content.get("dimensions"), dict), f"{code}: dimensions 应为 dict"

    @pytest.mark.parametrize("code", list(_load_all_scenarios().keys()))
    def test_stats_has_required_fields(self, code):
        data = _load_all_scenarios()[code]
        stats = data.get("stats", {})
        missing = self.SCENARIO_REQUIRED_STATS - set(stats.keys())
        assert not missing, f"{code}: stats 缺少字段: {missing}"

    @pytest.mark.parametrize("code", list(_load_all_scenarios().keys()))
    def test_satisfaction_in_range(self, code):
        data = _load_all_scenarios()[code]
        satisfaction = data.get("stats", {}).get("satisfaction", -1)
        assert 0.0 <= satisfaction <= 1.0, \
            f"{code}: satisfaction={satisfaction} 不在 [0.0, 1.0]"

    def test_filename_matches_code(self):
        for f in SCENARIOS_DIR.glob("*.yaml"):
            data = _load_yaml(f)
            if not data:
                continue
            assert data.get("code") == f.stem, \
                f"{f.name}: code 不匹配文件名"

    def test_all_industry_is_fmcg(self):
        for f in SCENARIOS_DIR.glob("*.yaml"):
            data = _load_yaml(f)
            if not data:
                continue
            assert data.get("industry") == "fmcg", \
                f"{f.name}: industry={data.get('industry')} != 'fmcg'"


# ═══════════════════════════════════════════════════════════════
# P0 — 交叉引用完整性
# ═══════════════════════════════════════════════════════════════


@pytest.mark.p0
class TestCrossReferenceIntegrity:
    """验证 indicator / scenario / intent-routing 之间的引用完整性"""

    @pytest.fixture(scope="class")
    def indicator_codes(self):
        return set(_load_all_indicators().keys())

    @pytest.fixture(scope="class")
    def scenario_codes(self):
        return set(_load_all_scenarios().keys())

    @pytest.fixture(scope="class")
    def intent_routing(self):
        return _load_intent_routing()

    def test_scenario_required_indicators_exist(self, indicator_codes):
        for code, data in _load_all_scenarios().items():
            required = data.get("content", {}).get("required", [])
            for ind in required:
                assert ind in indicator_codes, \
                    f"scenario '{code}': required indicator '{ind}' 不存在"

    def test_scenario_optional_indicators_exist(self, indicator_codes):
        for code, data in _load_all_scenarios().items():
            optional = data.get("content", {}).get("optional", [])
            for ind in optional:
                assert ind in indicator_codes, \
                    f"scenario '{code}': optional indicator '{ind}' 不存在"

    def test_intent_routing_indicators_exist(self, indicator_codes, intent_routing):
        if not intent_routing:
            pytest.skip("intent-routing.yaml 不可解析")
        for intent in intent_routing.get("intents", []):
            for ind in intent.get("default_indicators", []):
                assert ind in indicator_codes, \
                    f"intent '{intent['id']}': indicator '{ind}' 不存在"

    def test_intent_routing_scenarios_exist(self, scenario_codes, intent_routing):
        if not intent_routing:
            pytest.skip("intent-routing.yaml 不可解析")
        for intent in intent_routing.get("intents", []):
            for scn in intent.get("default_scenarios", []):
                assert scn in scenario_codes, \
                    f"intent '{intent['id']}': scenario '{scn}' 不存在"

    def test_intent_routing_analysis_types_valid(self, intent_routing):
        if not intent_routing:
            pytest.skip("intent-routing.yaml 不可解析")
        valid = {"descriptive", "diagnostic", "predictive", "prescriptive", "exploratory"}
        for intent in intent_routing.get("intents", []):
            at = intent.get("analysis_type", "")
            assert at in valid, \
                f"intent '{intent['id']}': analysis_type='{at}' 非法"

    def test_intent_ids_unique(self, intent_routing):
        if not intent_routing:
            pytest.skip("intent-routing.yaml 不可解析")
        ids = [i["id"] for i in intent_routing.get("intents", [])]
        duplicates = {x for x in ids if ids.count(x) > 1}
        assert not duplicates, f"重复的 intent id: {duplicates}"

    def test_analysis_type_chains_complete(self, intent_routing):
        if not intent_routing:
            pytest.skip("intent-routing.yaml 不可解析")
        chains = intent_routing.get("analysis_type_chains", {})
        expected_types = {"descriptive", "diagnostic", "predictive", "prescriptive", "exploratory"}
        missing = expected_types - set(chains.keys())
        assert not missing, f"analysis_type_chains 缺失类型: {missing}"

    def test_model_files_exist_or_null(self, intent_routing):
        if not intent_routing:
            pytest.skip("intent-routing.yaml 不可解析")
        for model_key, rel_path in intent_routing.get("model_files", {}).items():
            if rel_path is None:
                continue  # null 值允许 (如 funnel-model, rfm-model)
            if "?" in str(rel_path):
                # 标记为待创建, 不算错误
                continue
            full_path = PROJECT_ROOT / rel_path
            assert full_path.exists(), \
                f"model '{model_key}': 文件不存在 {rel_path}"


# ═══════════════════════════════════════════════════════════════
# P1 — 数据一致性
# ═══════════════════════════════════════════════════════════════


@pytest.mark.p1
class TestDataConsistency:
    """数据一致性检查 — 非阻断性"""

    @pytest.fixture(scope="class")
    def indicator_codes(self):
        return set(_load_all_indicators().keys())

    @pytest.fixture(scope="class")
    def intent_routing(self):
        return _load_intent_routing()

    def test_no_orphan_indicators(self, indicator_codes, intent_routing):
        """检测未被任何 scenario 或 intent 引用的指标 (警告, 不失败)"""
        referenced = set()

        for _, data in _load_all_scenarios().items():
            content = data.get("content", {})
            referenced.update(content.get("required", []))
            referenced.update(content.get("optional", []))

        if intent_routing:
            for intent in intent_routing.get("intents", []):
                referenced.update(intent.get("default_indicators", []))

        orphans = indicator_codes - referenced
        # 维度型指标 (order_id, user_id, status 等) 天然不被场景引用
        # 这里仅记录, 不硬失败
        if orphans:
            orphan_list = sorted(orphans)
            print(f"\n  ⚠ 未被引用的指标 ({len(orphans)}): {', '.join(orphan_list)}")

    def test_formula_references_plausible(self, indicator_codes):
        """公式中引用的 token 要么是已知 indicator code, 要么是 SQL 关键字"""
        code_pattern = re.compile(r'([a-z][a-z_]+)')
        unresolvable_by_indicator = {}

        for code, data in _load_all_indicators().items():
            formula = data.get("definition", {}).get("formula", "")
            tokens = set(code_pattern.findall(formula))
            unknown = tokens - indicator_codes - SQL_KEYWORDS
            if unknown:
                unresolvable_by_indicator[code] = sorted(unknown)

        if unresolvable_by_indicator:
            print(f"\n  ⚠ Formula 中未识别的 token (可能是概念名):")
            for ind, tokens in sorted(unresolvable_by_indicator.items()):
                print(f"    {ind}: {', '.join(tokens)}")

    def test_intent_skill_chains_valid(self, intent_routing):
        """intent 中的 skill_chain 引用的 skill 应存在"""
        if not intent_routing:
            pytest.skip("intent-routing.yaml 不可解析")

        existing_skills = _get_existing_skills()
        for intent in intent_routing.get("intents", []):
            for skill in intent.get("skill_chain", []):
                assert skill in existing_skills, \
                    f"intent '{intent['id']}': skill '{skill}' 不存在于 skills/"

    def test_analysis_type_chains_skills_valid(self, intent_routing):
        """analysis_type_chains 中的 skill 应存在"""
        if not intent_routing:
            pytest.skip("intent-routing.yaml 不可解析")

        existing_skills = _get_existing_skills()
        for at, chain in intent_routing.get("analysis_type_chains", {}).items():
            for skill in chain:
                assert skill in existing_skills, \
                    f"analysis_type '{at}' chain: skill '{skill}' 不存在"


# ═══════════════════════════════════════════════════════════════
# P2 — 数据质量
# ═══════════════════════════════════════════════════════════════


@pytest.mark.p2
class TestStatsQuality:
    """stats 字段数据质量检查"""

    def test_importance_distribution(self):
        """低 importance 指标应引起关注"""
        low_importance = []
        for code, data in _load_all_indicators().items():
            imp = data.get("stats", {}).get("importance", 0)
            if imp < 0.5:
                low_importance.append((code, imp))

        if low_importance:
            items = ", ".join(f"{c}({i:.2f})" for c, i in sorted(low_importance))
            print(f"\n  ⚠ importance < 0.5 的指标: {items}")

    def test_updated_dates_recent(self):
        """updated 日期不应超过 90 天"""
        cutoff = date.today() - timedelta(days=90)
        stale = []
        for code, data in _load_all_indicators().items():
            updated_str = str(data.get("stats", {}).get("updated", ""))
            try:
                updated = date.fromisoformat(updated_str)
                if updated < cutoff:
                    stale.append((code, updated_str))
            except (ValueError, TypeError):
                stale.append((code, f"无效日期: {updated_str}"))

        if stale:
            items = ", ".join(f"{c}({d})" for c, d in sorted(stale))
            print(f"\n  ⚠ 超过 90 天未更新的指标: {items}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
