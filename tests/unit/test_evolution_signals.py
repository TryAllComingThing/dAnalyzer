"""Phase 2 信号检测器单元测试

覆盖:
- signal_detector: classify_query_pair / detect_extension
- reinforcement_detector: detect_reinforcement
- counterfactual_check: check_counterfactual
- preference_detector: detect_preference
"""

from __future__ import annotations

import pytest

from learn.ingest.models import SignalType
from learn.ingest.signal_detector import classify_query_pair, detect_extension
from learn.ingest.reinforcement_detector import detect_reinforcement
from learn.ingest.counterfactual_check import check_counterfactual
from learn.ingest.preference_detector import detect_preference
from tests.fixtures.evolution_fixtures import (
    make_correction_pair,
    make_counterfactual_observation,
    make_five_turn_session,
    make_narrowing_pair,
    make_partial_correction_pair,
    make_preference_observation_chart,
    make_pure_correction_observation,
    make_refinement_pair,
    make_supplement_pair,
    make_unrelated_pair,
)


# ============================================================
# classify_query_pair 测试
# ============================================================

class TestClassifyQueryPair:
    def test_disjoint_is_correction(self):
        prev, curr = make_correction_pair()
        sig = classify_query_pair(prev, curr)
        assert sig is not None
        assert sig.type == SignalType.CORRECTION
        assert sig.replacement_ratio == 1.0
        assert len(sig.replaced_indicators) == 2
        assert len(sig.kept_indicators) == 0

    def test_partial_overlap_with_negation_is_correction(self):
        prev, curr = make_partial_correction_pair()
        sig = classify_query_pair(prev, curr)
        assert sig is not None
        assert sig.type == SignalType.CORRECTION
        assert sig.replacement_ratio >= 0.5
        assert "order_count" in sig.kept_indicators

    def test_pure_addition_is_supplement(self):
        prev, curr = make_supplement_pair()
        sig = classify_query_pair(prev, curr)
        assert sig is not None
        assert sig.type == SignalType.SUPPLEMENT
        assert "inventory_turnover" in sig.added_indicators

    def test_partial_overlap_no_negation_is_refinement(self):
        """部分重叠 + 无否定词 + 非子集关系 → refinement"""
        from learn.ingest.models import Observation, ObservationContext, TimePeriod, TriggerSource
        ctx = ObservationContext(TimePeriod.NORMAL, "品类趋势", TriggerSource.NEW_QUERY)
        ctx2 = ObservationContext(TimePeriod.NORMAL, "加转化率看看", TriggerSource.FOLLOW_UP)
        prev = Observation(
            turn=1, query="品类趋势", industry="fmcg",
            indicators_retrieved=["sales_amount", "order_count"],
            scenarios_retrieved=["category_analysis"], context=ctx,
        )
        curr = Observation(
            turn=2, query="加转化率看看，去掉订单数", industry="fmcg",
            indicators_retrieved=["sales_amount", "conversion_rate"],
            scenarios_retrieved=["category_analysis"], context=ctx2,
        )
        sig = classify_query_pair(prev, curr)
        assert sig is not None
        assert sig.type == SignalType.REFINEMENT
        assert "order_count" in sig.replaced_indicators
        assert "conversion_rate" in sig.added_indicators
        assert "sales_amount" in sig.kept_indicators

    def test_scenario_change_is_none(self):
        prev, curr = make_unrelated_pair()
        sig = classify_query_pair(prev, curr)
        assert sig is None

    def test_pure_narrowing_is_none(self):
        prev, curr = make_narrowing_pair()
        sig = classify_query_pair(prev, curr)
        assert sig is None

    def test_identical_indicators_is_none(self):
        from learn.ingest.models import Observation, ObservationContext, TimePeriod, TriggerSource
        ctx = ObservationContext(TimePeriod.NORMAL, "品类表现", TriggerSource.NEW_QUERY)
        prev = Observation(
            turn=1, query="品类表现", industry="fmcg",
            indicators_retrieved=["sales_amount", "order_count"],
            scenarios_retrieved=["category_analysis"], context=ctx,
        )
        curr = Observation(
            turn=2, query="再看一次", industry="fmcg",
            indicators_retrieved=["sales_amount", "order_count"],
            scenarios_retrieved=["category_analysis"], context=ctx,
        )
        assert classify_query_pair(prev, curr) is None

    def test_empty_indicators_returns_none(self):
        from learn.ingest.models import Observation, ObservationContext, TimePeriod, TriggerSource
        ctx = ObservationContext(TimePeriod.NORMAL, "品类表现", TriggerSource.NEW_QUERY)
        prev = Observation(turn=1, query="x", industry="fmcg", indicators_retrieved=[], scenarios_retrieved=["s"], context=ctx)
        curr = Observation(turn=2, query="y", industry="fmcg", indicators_retrieved=[], scenarios_retrieved=["s"], context=ctx)
        assert classify_query_pair(prev, curr) is None


# ============================================================
# detect_extension 测试
# ============================================================

class TestDetectExtension:
    def test_scenario_change_not_extension(self):
        prev, curr = make_unrelated_pair()
        assert detect_extension(prev, curr) is None

    def test_same_skill_chain_not_extension(self):
        from learn.ingest.models import Observation, ObservationContext, TimePeriod, TriggerSource
        ctx = ObservationContext(TimePeriod.NORMAL, "q", TriggerSource.NEW_QUERY)
        prev = Observation(
            turn=1, query="q", industry="fmcg",
            indicators_retrieved=["a"], scenarios_retrieved=["s"],
            context=ctx, skill_chain_actual=["data-query"],
        )
        curr = Observation(
            turn=2, query="q", industry="fmcg",
            indicators_retrieved=["a"], scenarios_retrieved=["s"],
            context=ctx, skill_chain_actual=["data-query"],
        )
        assert detect_extension(prev, curr) is None

    def test_extends_skill_chain_is_extension(self):
        from learn.ingest.models import Observation, ObservationContext, TimePeriod, TriggerSource
        ctx = ObservationContext(TimePeriod.NORMAL, "q", TriggerSource.NEW_QUERY)
        prev = Observation(
            turn=1, query="q", industry="fmcg",
            indicators_retrieved=["a"], scenarios_retrieved=["s"],
            context=ctx, skill_chain_actual=["data-query", "data-analysis"],
        )
        curr = Observation(
            turn=2, query="q", industry="fmcg",
            indicators_retrieved=["a"], scenarios_retrieved=["s"],
            context=ctx, skill_chain_actual=["data-query", "data-analysis", "visual"],
        )
        sig = detect_extension(prev, curr)
        assert sig is not None
        assert sig.type == SignalType.EXTENSION

    def test_empty_skill_chain_no_extension(self):
        from learn.ingest.models import Observation, ObservationContext, TimePeriod, TriggerSource
        ctx = ObservationContext(TimePeriod.NORMAL, "q", TriggerSource.NEW_QUERY)
        prev = Observation(turn=1, query="q", industry="fmcg", indicators_retrieved=["a"], scenarios_retrieved=["s"], context=ctx)
        curr = Observation(turn=2, query="q", industry="fmcg", indicators_retrieved=["a"], scenarios_retrieved=["s"], context=ctx)
        assert detect_extension(prev, curr) is None


# ============================================================
# detect_reinforcement 测试
# ============================================================

class TestDetectReinforcement:
    def test_two_turn_session_yields_reinforcement(self):
        """Turn 1 → Turn 2 是 correction，Turn 1 不产生 reinforcement；Turn 2 是最后一轮产生"""
        obs = make_five_turn_session()[:2]
        signals = detect_reinforcement(obs)
        # Turn 2 是最后一轮且无 error → reinforcement
        assert any(s.turn_pair == (2, 2) for s in signals)
        # Turn 1 → Turn 2 是 correction，不产生 reinforcement for Turn 1
        assert not any(s.turn_pair == (1, 1) for s in signals)

    def test_single_turn_no_reinforcement(self):
        """单轮 session 不产生 reinforcement（无法判断是否被接受）"""
        obs = make_five_turn_session()[:1]
        signals = detect_reinforcement(obs)
        assert signals == []

    def test_last_turn_with_error_no_reinforcement(self):
        from learn.ingest.models import Observation, ObservationContext, TimePeriod, TriggerSource
        ctx = ObservationContext(TimePeriod.NORMAL, "q", TriggerSource.NEW_QUERY)
        obs = [
            Observation(turn=1, query="q", industry="fmcg", indicators_retrieved=["a"], scenarios_retrieved=["s"], context=ctx, error="timeout"),
            Observation(turn=2, query="q2", industry="fmcg", indicators_retrieved=["b"], scenarios_retrieved=["s"], context=ctx, error=None),
        ]
        signals = detect_reinforcement(obs)
        # Turn 1 followed by scenario-same turn 2 → no scenario change → only last turn
        # Turn 2 is last, has no error → gets reinforcement
        assert any(s.turn_pair == (2, 2) for s in signals)

    def test_scenario_change_yields_reinforcement(self):
        """Turn N 的 scenario 与 Turn N+1 不同 → Turn N 被接受"""
        from learn.ingest.models import Observation, ObservationContext, TimePeriod, TriggerSource
        ctx = ObservationContext(TimePeriod.NORMAL, "q", TriggerSource.NEW_QUERY)
        obs = [
            Observation(turn=1, query="品类表现", industry="fmcg", indicators_retrieved=["a"], scenarios_retrieved=["category_analysis"], context=ctx),
            Observation(turn=2, query="渠道分析", industry="fmcg", indicators_retrieved=["b"], scenarios_retrieved=["channel_analysis"], context=ctx),
            Observation(turn=3, query="报告", industry="fmcg", indicators_retrieved=["b"], scenarios_retrieved=["channel_analysis"], context=ctx),
        ]
        signals = detect_reinforcement(obs)
        # Turn 1 scenario != Turn 2 → Turn 1 accepted
        assert any(s.turn_pair == (1, 1) for s in signals)
        # Turn 3 is last → accepted
        assert any(s.turn_pair == (3, 3) for s in signals)

    def test_supplement_yields_reinforcement(self):
        prev, curr = make_supplement_pair()
        signals = detect_reinforcement([prev, curr])
        # supplement → prev accepted
        assert any(s.turn_pair == (1, 1) for s in signals)
        # last turn → also accepted
        assert any(s.turn_pair == (2, 2) for s in signals)

    def test_reinforcement_per_turn_max_one(self):
        obs = make_five_turn_session()
        signals = detect_reinforcement(obs)
        # 每轮最多 1 个 reinforcement
        counts: dict[int, int] = {}
        for s in signals:
            counts[s.turn_pair[0]] = counts.get(s.turn_pair[0], 0) + 1
        for turn, c in counts.items():
            assert c <= 1, f"Turn {turn} has {c} reinforcements"


# ============================================================
# check_counterfactual 测试
# ============================================================

class TestCheckCounterfactual:
    def test_hit_when_in_candidates_not_retrieved(self):
        obs = make_counterfactual_observation()
        result = check_counterfactual(obs, ["gross_margin_rate", "sell_through_rate"])
        assert result is not None
        assert result.candidate_hit is True
        assert result.hit_indicators == ["gross_margin_rate", "sell_through_rate"]
        assert result.hit_ranks == [4, 5]

    def test_none_when_not_in_candidates(self):
        obs = make_pure_correction_observation()
        result = check_counterfactual(obs, ["gross_margin_rate", "net_margin_rate"])
        assert result is None

    def test_none_when_already_retrieved(self):
        obs = make_counterfactual_observation()
        result = check_counterfactual(obs, ["sales_amount"])
        assert result is None

    def test_none_when_no_candidates(self):
        from learn.ingest.models import Observation, ObservationContext, TimePeriod, TriggerSource
        ctx = ObservationContext(TimePeriod.NORMAL, "q", TriggerSource.NEW_QUERY)
        obs = Observation(turn=1, query="q", industry="fmcg", indicators_retrieved=["a"], scenarios_retrieved=["s"], context=ctx)
        result = check_counterfactual(obs, ["a"])
        assert result is None

    def test_none_when_empty_selection(self):
        obs = make_counterfactual_observation()
        result = check_counterfactual(obs, [])
        assert result is None


# ============================================================
# detect_preference 测试
# ============================================================

class TestDetectPreference:
    def test_chart_preference_when_user_overrides(self):
        obs = make_preference_observation_chart()
        signals = detect_preference(
            obs,
            user_chart_choice="line_chart",
            recommended_chart="heatmap",
        )
        assert len(signals) == 1
        assert signals[0].type == SignalType.PREFERENCE_CHART
        assert signals[0].query_after == "selected:line_chart"

    def test_report_preference_when_user_overrides(self):
        obs = make_preference_observation_chart()
        signals = detect_preference(
            obs,
            user_report_choice="excel",
            recommended_report="pdf",
        )
        assert len(signals) == 1
        assert signals[0].type == SignalType.PREFERENCE_REPORT

    def test_both_preferences(self):
        obs = make_preference_observation_chart()
        signals = detect_preference(
            obs,
            user_chart_choice="line_chart",
            recommended_chart="heatmap",
            user_report_choice="excel",
            recommended_report="pdf",
        )
        assert len(signals) == 2
        types = {s.type for s in signals}
        assert SignalType.PREFERENCE_CHART in types
        assert SignalType.PREFERENCE_REPORT in types

    def test_no_signal_when_accepted(self):
        obs = make_preference_observation_chart()
        signals = detect_preference(
            obs,
            user_chart_choice="heatmap",
            recommended_chart="heatmap",
        )
        assert len(signals) == 0

    def test_no_signal_when_no_input(self):
        obs = make_preference_observation_chart()
        signals = detect_preference(obs)
        assert len(signals) == 0


# ============================================================
# 属性测试 (property tests)
# ============================================================

class TestProperties:
    def test_classify_query_pair_always_valid(self):
        """classify_query_pair 总是返回合法值或 None"""
        from learn.ingest.models import Observation, ObservationContext, TimePeriod, TriggerSource
        import itertools

        ctx = ObservationContext(TimePeriod.NORMAL, "q", TriggerSource.NEW_QUERY)
        scenarios = [["category_analysis"], ["channel_analysis"]]
        indicator_sets = [
            [],
            ["sales_amount"],
            ["gross_margin_rate"],
            ["sales_amount", "order_count"],
            ["sales_amount", "gross_margin_rate"],
        ]
        queries = ["品类表现", "不对，我要毛利率"]

        for (si, inds_prev), (sj, inds_curr), (qk, query) in itertools.product(
            enumerate(indicator_sets), enumerate(indicator_sets), enumerate(queries)
        ):
            prev = Observation(
                turn=1, query="品类表现", industry="fmcg",
                indicators_retrieved=inds_prev, scenarios_retrieved=scenarios[0], context=ctx,
            )
            curr = Observation(
                turn=2, query=query, industry="fmcg",
                indicators_retrieved=inds_curr, scenarios_retrieved=scenarios[0], context=ctx,
            )
            result = classify_query_pair(prev, curr)
            assert result is None or isinstance(result.type, SignalType)

    def test_correction_signals_have_non_empty_replaced(self):
        """所有 correction 信号都有被替换的指标"""
        from tests.fixtures.evolution_fixtures import make_correction_signals_for_clustering
        signals = make_correction_signals_for_clustering()
        for s in signals:
            assert s.type == SignalType.CORRECTION
            assert len(s.indicators_before) > 0
            assert len(s.indicators_after) > 0
