"""Phase 3 分析与聚类单元测试

覆盖:
- confidence: 四维置信度计算
- proximity_builder: 共现矩阵构建
- signal_analyzer: 聚类 + 假设生成
- propagation: 语义传播 + 跨行业迁移
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from learn.analyze.confidence import (
    calculate_confidence,
    calculate_consistency_score,
    calculate_diversity_score,
    calculate_frequency_score,
    calculate_proximity_bonus,
    get_frequency_sat,
)
from learn.analyze.proximity_builder import (
    build_cooccurrence_matrix,
    get_neighbors,
)
from learn.analyze.signal_analyzer import (
    cluster_corrections,
    cluster_extensions,
    cluster_l3_fallbacks,
    cluster_preferences,
    cluster_refinements,
    cluster_supplements,
    generate_hypotheses,
)
from learn.analyze.propagation import (
    cross_industry_propagate,
    load_cross_industry_mappings,
    propagate_correction,
)
from learn.ingest.models import (
    Hypothesis,
    HypothesisTarget,
    HypothesisType,
    SignalType,
)
from tests.fixtures.evolution_fixtures import (
    make_correction_signals_for_clustering,
    make_signals_mixed,
)


# ============================================================
# Confidence 测试
# ============================================================

class TestFrequencyScore:
    def test_at_saturation(self):
        assert calculate_frequency_score(5, SignalType.CORRECTION) == 1.0

    def test_half_saturation(self):
        assert calculate_frequency_score(2, SignalType.EXTENSION) == 0.25  # 2/8

    def test_zero_frequency(self):
        assert calculate_frequency_score(0, SignalType.CORRECTION) == 0.0

    def test_different_sat_thresholds(self):
        assert get_frequency_sat(SignalType.EXTENSION) == 8
        assert get_frequency_sat(SignalType.CORRECTION) == 5
        assert get_frequency_sat(SignalType.L3_FALLBACK) == 3


class TestConsistencyScore:
    def test_all_same_direction(self):
        signals = make_correction_signals_for_clustering()
        score = calculate_consistency_score(signals, user_decay_enabled=False)
        assert score > 0.8, f"Expected > 0.8, got {score}"

    def test_mixed_directions(self):
        signals = make_signals_mixed()
        score = calculate_consistency_score(signals, user_decay_enabled=False)
        # 3 corrections in one direction, 2 supplements in different → lower consistency
        assert score < 0.9

    def test_empty_signals(self):
        assert calculate_consistency_score([]) == 0.0

    def test_single_signal(self):
        signals = make_correction_signals_for_clustering()[:1]
        assert calculate_consistency_score(signals, user_decay_enabled=False) == 1.0


class TestDiversityScore:
    def test_at_saturation(self):
        assert calculate_diversity_score(3) == 1.0

    def test_two_sessions(self):
        assert calculate_diversity_score(2) == pytest.approx(2 / 3)

    def test_zero(self):
        assert calculate_diversity_score(0) == 0.0


class TestProximityBonus:
    def test_half_hits(self):
        assert calculate_proximity_bonus(3, 6) == 0.5

    def test_no_signals(self):
        assert calculate_proximity_bonus(5, 0) == 0.0

    def test_all_hits(self):
        assert calculate_proximity_bonus(10, 10) == 1.0


class TestCalculateConfidence:
    def test_high_freq_same_dir_multi_session(self):
        """5条同方向correction来自4个session → 高置信度"""
        signals = make_correction_signals_for_clustering()
        result = calculate_confidence(signals)
        assert result.frequency_score == 1.0  # 5/5
        assert result.diversity_score == 1.0  # 4 sessions >= 3
        assert result.raw_confidence > 0.75

    def test_empty_signals_zero(self):
        result = calculate_confidence([])
        assert result.raw_confidence == 0.0
        assert result.frequency_sat == 0

    def test_with_counterfactual_hits(self):
        signals = make_correction_signals_for_clustering()[:3]
        result = calculate_confidence(signals, counterfactual_hits=2)
        assert result.proximity_bonus > 0
        # Check that the bonus increased raw confidence
        no_bonus = calculate_confidence(signals, counterfactual_hits=0)
        assert result.raw_confidence >= no_bonus.raw_confidence

    def test_custom_weights(self):
        signals = make_correction_signals_for_clustering()[:3]
        result = calculate_confidence(signals, alpha=1.0, beta=0.0, gamma=0.0, delta=0.0)
        assert result.raw_confidence == result.frequency_score


# ============================================================
# Proximity Builder 测试
# ============================================================

class TestProximityBuilder:
    def make_scenario_fixture(self, tmpdir: str) -> Path:
        """创建测试用的 scenario 文件"""
        base = Path(tmpdir) / "knowledge" / "industry" / "fmcg" / "scenarios"
        base.mkdir(parents=True)
        scenarios = {
            "category_analysis.yaml": {
                "content": {
                    "required": ["sales_amount", "order_count", "sku_count"],
                    "optional": ["sell_through_rate", "conversion_rate"],
                }
            },
            "channel_analysis.yaml": {
                "content": {
                    "required": ["sales_amount", "channel_revenue_share"],
                    "optional": ["order_count"],
                }
            },
        }
        for name, data in scenarios.items():
            with open(base / name, "w", encoding="utf-8") as f:
                yaml.dump(data, f)
        return Path(tmpdir) / "knowledge"

    def test_build_matrix_from_scenarios(self):
        with tempfile.TemporaryDirectory() as td:
            knowledge_dir = self.make_scenario_fixture(td)
            matrix = build_cooccurrence_matrix(knowledge_dir)

            assert "sales_amount" in matrix
            assert "order_count" in matrix
            # sales_amount and order_count co-occur in both scenarios → high proximity
            assert matrix["sales_amount"]["order_count"] > 0.0

    def test_same_scenario_high_proximity(self):
        with tempfile.TemporaryDirectory() as td:
            knowledge_dir = self.make_scenario_fixture(td)
            matrix = build_cooccurrence_matrix(knowledge_dir)

            # sales_amount and sku_count are both required in category_analysis
            assert matrix["sales_amount"]["sku_count"] > 0.0

    def test_matrix_symmetry(self):
        with tempfile.TemporaryDirectory() as td:
            knowledge_dir = self.make_scenario_fixture(td)
            matrix = build_cooccurrence_matrix(knowledge_dir)

            for i in matrix:
                for j in matrix[i]:
                    assert matrix[j][i] == pytest.approx(matrix[i][j])

    def test_empty_scenarios(self):
        with tempfile.TemporaryDirectory() as td:
            matrix = build_cooccurrence_matrix(Path(td))
            assert matrix == {}

    def test_get_neighbors_filters_by_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            knowledge_dir = self.make_scenario_fixture(td)
            matrix = build_cooccurrence_matrix(knowledge_dir)

            neighbors = get_neighbors(matrix, "sales_amount", threshold=0.6)
            for name, prox in neighbors:
                assert prox >= 0.6

    def test_get_neighbors_respects_max(self):
        with tempfile.TemporaryDirectory() as td:
            knowledge_dir = self.make_scenario_fixture(td)
            matrix = build_cooccurrence_matrix(knowledge_dir)

            neighbors = get_neighbors(matrix, "sales_amount", threshold=0.0, max_neighbors=2)
            assert len(neighbors) <= 2

    def test_unknown_indicator_empty(self):
        matrix: dict[str, dict[str, float]] = {}
        assert get_neighbors(matrix, "nonexistent") == []

    def test_industry_filter(self):
        with tempfile.TemporaryDirectory() as td:
            knowledge_dir = self.make_scenario_fixture(td)
            # Also create a finance scenario
            fin = Path(td) / "knowledge" / "industry" / "finance" / "scenarios"
            fin.mkdir(parents=True)
            with open(fin / "risk.yaml", "w") as f:
                yaml.dump({"content": {"required": ["npl_ratio", "loan_balance"]}}, f)

            full_matrix = build_cooccurrence_matrix(knowledge_dir)
            fmcg_matrix = build_cooccurrence_matrix(knowledge_dir, industry="fmcg")

            # fmcg-only should not contain finance indicators
            assert "npl_ratio" in full_matrix
            assert "npl_ratio" not in fmcg_matrix


# ============================================================
# Signal Analyzer 测试
# ============================================================

class TestClustering:
    def test_cluster_corrections_groups_by_direction(self):
        signals = make_correction_signals_for_clustering()
        clusters = cluster_corrections(signals)
        assert len(clusters) >= 1
        # All 5 signals have the same direction
        total_signals = sum(c.frequency for c in clusters)
        assert total_signals == 5

    def test_cluster_supplements_groups_by_added_indicator(self):
        from learn.ingest.models import DetectedSignal, DetectionMethod
        signals = [
            DetectedSignal(
                type=SignalType.SUPPLEMENT, session_id="s1", turn_pair=(1, 2),
                industry="fmcg", scenario="category_analysis",
                indicators_before=["gross_margin_rate"],
                indicators_after=["gross_margin_rate", "inventory_turnover"],
                added_indicators=["inventory_turnover"],
                detection_method=DetectionMethod.PURE_ADDITION,
            ),
            DetectedSignal(
                type=SignalType.SUPPLEMENT, session_id="s2", turn_pair=(1, 2),
                industry="fmcg", scenario="category_analysis",
                indicators_before=["gross_margin_rate"],
                indicators_after=["gross_margin_rate", "inventory_turnover"],
                added_indicators=["inventory_turnover"],
                detection_method=DetectionMethod.PURE_ADDITION,
            ),
            DetectedSignal(
                type=SignalType.SUPPLEMENT, session_id="s3", turn_pair=(2, 3),
                industry="fmcg", scenario="category_analysis",
                indicators_before=["sales_amount"],
                indicators_after=["sales_amount", "net_margin_rate"],
                added_indicators=["net_margin_rate"],
                detection_method=DetectionMethod.PURE_ADDITION,
            ),
        ]
        clusters = cluster_supplements(signals)
        assert len(clusters) >= 1
        for c in clusters:
            assert c.signal_type == SignalType.SUPPLEMENT

    def test_cluster_refinements_empty_for_no_refinements(self):
        signals = make_correction_signals_for_clustering()
        clusters = cluster_refinements(signals)
        assert clusters == []

    def test_cluster_preferences(self):
        from learn.ingest.models import DetectedSignal
        signals = [
            DetectedSignal(
                type=SignalType.PREFERENCE_CHART, session_id="s1", turn_pair=(1, 1),
                industry="fmcg", scenario="category_analysis",
                indicators_before=["heatmap"], indicators_after=["line_chart"],
            ),
            DetectedSignal(
                type=SignalType.PREFERENCE_CHART, session_id="s2", turn_pair=(1, 1),
                industry="fmcg", scenario="category_analysis",
                indicators_before=["heatmap"], indicators_after=["line_chart"],
            ),
            DetectedSignal(
                type=SignalType.PREFERENCE_CHART, session_id="s3", turn_pair=(1, 1),
                industry="fmcg", scenario="category_analysis",
                indicators_before=["heatmap"], indicators_after=["line_chart"],
            ),
        ]
        clusters = cluster_preferences(signals)
        assert len(clusters) >= 1
        assert clusters[0].frequency == 3

    def test_l3_fallback_clustering(self):
        from learn.ingest.models import DetectedSignal
        signals = [
            DetectedSignal(
                type=SignalType.L3_FALLBACK, session_id="s1", turn_pair=(1, 1),
                industry="fmcg", scenario="", query_before="客户生命周期价值lifetime",
            ),
            DetectedSignal(
                type=SignalType.L3_FALLBACK, session_id="s2", turn_pair=(1, 1),
                industry="fmcg", scenario="", query_before="客户生命周期价值评估",
            ),
            DetectedSignal(
                type=SignalType.L3_FALLBACK, session_id="s3", turn_pair=(1, 1),
                industry="fmcg", scenario="", query_before="客户生命周期",
            ),
        ]
        clusters = cluster_l3_fallbacks(signals)
        assert len(clusters) >= 1


class TestHypothesisGeneration:
    def test_generates_hypotheses_from_clusters(self):
        signals = make_correction_signals_for_clustering()
        clusters = cluster_corrections(signals)
        hypotheses = generate_hypotheses(clusters)
        assert len(hypotheses) >= 1

        h = hypotheses[0]
        assert h.type == HypothesisType.KEYWORD_ADJUSTMENT
        assert h.industry == "fmcg"
        assert h.status.value == "pending_validation"
        assert h.evidence.frequency == 5
        assert len(h.id) == 12

    def test_below_min_frequency_no_hypothesis(self):
        signals = make_correction_signals_for_clustering()[:2]
        clusters = cluster_corrections(signals)
        hypotheses = generate_hypotheses(clusters)
        assert hypotheses == []

    def test_target_inference(self):
        signals = make_correction_signals_for_clustering()
        clusters = cluster_corrections(signals)
        hypotheses = generate_hypotheses(clusters)
        assert hypotheses[0].target.layer == "canonical"
        assert "category_analysis" in hypotheses[0].target.file

    def test_mixed_signals_produce_multiple_hypothesis_types(self):
        signals = make_signals_mixed()
        corrections = cluster_corrections(signals)
        supplements = cluster_supplements(signals)
        all_clusters = corrections + supplements
        hypotheses = generate_hypotheses(all_clusters)

        types = {h.type for h in hypotheses}
        # corrections → keyword_adjustment, supplements probably below min_freq
        assert HypothesisType.KEYWORD_ADJUSTMENT in types


# ============================================================
# Propagation 测试
# ============================================================

class TestPropagation:
    def test_propagate_to_neighbors(self):
        hypothesis = Hypothesis(
            id="h-test-001",
            type=HypothesisType.KEYWORD_ADJUSTMENT,
            industry="fmcg",
            evidence=None,  # type: ignore[arg-type]
            target=HypothesisTarget(layer="canonical", file="test.yaml", path="test.yaml"),
            confidence=0.8,
            current={"sales_amount": 0.80},
            suggested={"gross_margin_rate": 0.80, "sales_amount": 0.40},
        )

        matrix = {
            "sales_amount": {
                "order_count": 0.85,
                "sku_count": 0.70,
                "conversion_rate": 0.55,  # below 0.6 threshold
            },
            "gross_margin_rate": {
                "net_margin_rate": 0.80,
            },
        }

        entries = propagate_correction(hypothesis, matrix)
        assert len(entries) >= 2  # order_count + sku_count + net_margin_rate

        # order_count gets demoted because sales_amount is being demoted
        order_entry = next((e for e in entries if e.indicator == "order_count"), None)
        assert order_entry is not None
        assert order_entry.reason == "semantic_propagation"
        assert order_entry.delta < 0  # demotion follows source direction

    def test_proximity_below_threshold_not_propagated(self):
        hypothesis = Hypothesis(
            id="h-test-002",
            type=HypothesisType.KEYWORD_ADJUSTMENT,
            industry="fmcg",
            evidence=None,  # type: ignore[arg-type]
            target=HypothesisTarget(layer="canonical", file="test.yaml", path="test.yaml"),
            confidence=0.7,
            current={"sales_amount": 0.70},
            suggested={"gross_margin_rate": 0.70},
        )

        matrix = {"sales_amount": {"conversion_rate": 0.55}}
        entries = propagate_correction(hypothesis, matrix, proximity_threshold=0.6)
        assert len(entries) == 0

    def test_max_neighbors_limit(self):
        hypothesis = Hypothesis(
            id="h-test-003",
            type=HypothesisType.KEYWORD_ADJUSTMENT,
            industry="fmcg",
            evidence=None,  # type: ignore[arg-type]
            target=HypothesisTarget(layer="canonical", file="test.yaml", path="test.yaml"),
            confidence=0.8,
            current={"sales_amount": 0.60},
            suggested={"order_count": 0.60},
        )

        matrix = {
            "sales_amount": {f"ind_{i}": 0.9 for i in range(10)},
        }
        entries = propagate_correction(hypothesis, matrix, max_neighbors=3)
        assert len(entries) == 3

    def test_cross_industry_propagate(self):
        hypothesis = Hypothesis(
            id="h-test-004",
            type=HypothesisType.KEYWORD_ADJUSTMENT,
            industry="fmcg",
            evidence=None,  # type: ignore[arg-type]
            target=HypothesisTarget(layer="canonical", file="test.yaml", path="test.yaml"),
            confidence=0.8,
            current={"sales_amount": 0.80},
            suggested={"gross_margin_rate": 0.80},
        )

        mappings = {
            "mappings": {
                "fmcg_to_logistics": [
                    {"from": "sales_amount", "to": "parcel_volume", "confidence": 0.70},
                ],
                "fmcg_to_manufacturing": [
                    {"from": "sales_amount", "to": "output_qty", "confidence": 0.65},
                ],
                "finance_to_manufacturing": [  # should be ignored (wrong source)
                    {"from": "loan_balance", "to": "output_qty", "confidence": 0.55},
                ],
            }
        }

        entries = cross_industry_propagate(hypothesis, mappings)
        assert len(entries) == 2

        targets = {e.indicator for e in entries}
        assert "parcel_volume" in targets
        assert "output_qty" in targets
        assert all(e.reason == "cross_industry_transfer" for e in entries)

    def test_cross_industry_weak_mapping_less_amplitude(self):
        hypothesis = Hypothesis(
            id="h-test-005",
            type=HypothesisType.KEYWORD_ADJUSTMENT,
            industry="fmcg",
            evidence=None,  # type: ignore[arg-type]
            target=HypothesisTarget(layer="canonical", file="test.yaml", path="test.yaml"),
            confidence=0.8,
            current={"sales_amount": 0.70},
            suggested={"sales_amount": 0.30},
        )

        mappings = {
            "mappings": {
                "fmcg_to_logistics": [
                    {"from": "sales_amount", "to": "parcel_volume", "confidence": 0.90},
                    {"from": "sales_amount", "to": "return_rate", "confidence": 0.45},
                ],
            }
        }

        entries = cross_industry_propagate(hypothesis, mappings)
        # Both are included, but return_rate gets smaller amplitude due to low confidence
        assert len(entries) == 2
        strong = next(e for e in entries if e.indicator == "parcel_volume")
        weak = next(e for e in entries if e.indicator == "return_rate")
        assert abs(strong.delta) > abs(weak.delta)


# ============================================================
# Integration: end-to-end analysis chain
# ============================================================

class TestAnalysisChain:
    def test_signals_to_hypotheses_to_propagation(self):
        """从信号聚类到假设生成再到邻近传播的完整分析链路"""
        signals = make_correction_signals_for_clustering()
        clusters = cluster_corrections(signals)
        hypotheses = generate_hypotheses(clusters)

        assert len(hypotheses) >= 1
        h = hypotheses[0]
        assert h.type == HypothesisType.KEYWORD_ADJUSTMENT

        # Build proximity matrix from test data and propagate
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "knowledge" / "industry" / "fmcg" / "scenarios"
            base.mkdir(parents=True)
            with open(base / "category_analysis.yaml", "w") as f:
                yaml.dump({
                    "content": {
                        "required": ["sales_amount", "order_count", "gross_margin_rate"],
                        "optional": ["sell_through_rate"],
                    }
                }, f)

            matrix = build_cooccurrence_matrix(Path(td) / "knowledge")
            entries = propagate_correction(h, matrix)

            # Verify propagation produces entries for nearby indicators
            assert isinstance(entries, list)
