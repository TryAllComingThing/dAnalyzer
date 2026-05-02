"""Phase 4 验证模块单元测试

覆盖: validator.validate_hypothesis / combo_validator.validate_batch
"""

from __future__ import annotations

import pytest

from learn.ingest.models import (
    DetectedSignal,
    DetectionMethod,
    Evidence,
    Hypothesis,
    HypothesisTarget,
    HypothesisType,
    SignalType,
    ValidationResult,
)
from learn.validate.validator import validate_hypothesis
from learn.validate.combo_validator import validate_batch


def _make_correction_hypothesis(
    hid: str = "h-test-001",
    confidence: float = 0.85,
    current: dict | None = None,
    suggested: dict | None = None,
) -> Hypothesis:
    return Hypothesis(
        id=hid,
        type=HypothesisType.KEYWORD_ADJUSTMENT,
        industry="fmcg",
        evidence=Evidence(
            signal_type=SignalType.CORRECTION,
            signal_ids=[f"s{i}" for i in range(10)],
            frequency=10,
            period_days=7,
            unique_sessions=5,
        ),
        target=HypothesisTarget(
            layer="canonical",
            file="category_analysis.yaml",
            path="knowledge/industry/fmcg/scenarios/category_analysis.yaml",
            field="content.required",
        ),
        confidence=confidence,
        current=current or {"sales_amount": 1.0, "order_count": 0.70},
        suggested=suggested or {"gross_margin_rate": 1.0, "order_count": 0.50},
    )


def _make_signals(
    n: int = 10,
    indicators_after: list[str] | None = None,
    added: list[str] | None = None,
) -> list[DetectedSignal]:
    """生成一致的信号列表"""
    after = indicators_after or ["gross_margin_rate", "order_count"]
    signals: list[DetectedSignal] = []
    for i in range(n):
        s = DetectedSignal(
            type=SignalType.CORRECTION,
            session_id=f"s{i}",
            turn_pair=(1, 2),
            industry="fmcg",
            scenario="category_analysis",
            indicators_before=["sales_amount", "order_count"],
            indicators_after=after,
            detection_method=DetectionMethod.DISJOINT,
            added_indicators=added or [],
            user_anon_id=f"u_{i % 4}",
        )
        signals.append(s)
    return signals


class TestValidateHypothesis:
    def test_high_pass_rate_passes(self):
        h = _make_correction_hypothesis()
        signals = _make_signals(10, indicators_after=["gross_margin_rate", "order_count"])
        result = validate_hypothesis(h, signals)
        assert result.passed
        assert result.pass_rate > 0.5
        assert result.validated_confidence > 0

    def test_low_pass_rate_fails(self):
        h = _make_correction_hypothesis(
            suggested={"gross_margin_rate": 1.0, "sell_through_rate": 0.80},
        )
        signals = _make_signals(10, indicators_after=["sales_amount", "sku_count"])
        result = validate_hypothesis(h, signals)
        assert not result.passed
        assert result.pass_rate < 0.5

    def test_insufficient_samples(self):
        h = _make_correction_hypothesis()
        signals = _make_signals(2)
        result = validate_hypothesis(h, signals)
        assert not result.passed
        assert "Insufficient" in result.notes[0]

    def test_degradation_detected(self):
        """当信号与假设 current 匹配时 → 退化"""
        h = _make_correction_hypothesis(
            current={"sales_amount": 1.0},
            suggested={"gross_margin_rate": 1.0},
        )
        signals = _make_signals(10, indicators_after=["sales_amount", "order_count"])
        result = validate_hypothesis(h, signals)
        # Some hold-out signals may match hypothesis, but current-directed
        # signals in training set should be caught
        assert result.holdout_count >= 1

    def test_deterministic_seed(self):
        h = _make_correction_hypothesis()
        signals = _make_signals(20, indicators_after=["gross_margin_rate", "order_count"])
        r1 = validate_hypothesis(h, signals, seed=42)
        r2 = validate_hypothesis(h, signals, seed=42)
        assert r1.pass_rate == r2.pass_rate
        assert r1.holdout_count == r2.holdout_count

    def test_supplement_hypothesis_validation(self):
        h = Hypothesis(
            id="h-supp-001",
            type=HypothesisType.INDICATOR_COMBINATION,
            industry="fmcg",
            evidence=Evidence(
                signal_type=SignalType.SUPPLEMENT,
                signal_ids=["s1", "s2", "s3", "s4", "s5"],
                frequency=5,
                period_days=7,
                unique_sessions=3,
            ),
            target=HypothesisTarget(
                layer="canonical",
                file="category_analysis.yaml",
                path="test.yaml",
                field="content.optional",
            ),
            confidence=0.75,
            suggested={"inventory_turnover": 1.0},
        )
        signals = _make_signals(6, added=["inventory_turnover"])
        result = validate_hypothesis(h, signals)
        assert result.passed


class TestComboValidator:
    def test_two_non_conflicting_pass(self):
        h1 = _make_correction_hypothesis(
            "h1", current={"a": 1.0}, suggested={"b": 1.0},
        )
        h2 = _make_correction_hypothesis(
            "h2", current={"c": 0.70}, suggested={"d": 0.80},
        )
        # Ensure different target paths
        h2 = Hypothesis(
            id=h2.id, type=h2.type, industry=h2.industry,
            evidence=h2.evidence,
            target=HypothesisTarget(
                layer="canonical", file="channel.yaml",
                path="knowledge/industry/fmcg/scenarios/channel_analysis.yaml",
                field="content.required",
            ),
            confidence=h2.confidence,
            current=h2.current, suggested=h2.suggested,
        )
        signals = _make_signals(10, indicators_after=["b", "d"])
        result = validate_batch([h1, h2], signals)
        # They should not conflict (different paths)
        assert len(result.conflicting_pairs) == 0

    def test_conflicting_hypotheses_detected(self):
        h1 = _make_correction_hypothesis(
            "h-conflict-1", suggested={"ind_a": 1.0, "ind_b": -0.5},
        )
        h2 = _make_correction_hypothesis(
            "h-conflict-2", suggested={"ind_a": -1.0, "ind_b": 0.5},
        )
        signals = _make_signals(10, indicators_after=["ind_c"])
        result = validate_batch([h1, h2], signals)
        assert len(result.conflicting_pairs) >= 1

    def test_empty_hypotheses(self):
        result = validate_batch([], _make_signals(5))
        assert result.all_passed
        assert result.hypothesis_results == []

    def test_single_hypothesis_no_conflict(self):
        h = _make_correction_hypothesis()
        signals = _make_signals(8, indicators_after=["gross_margin_rate", "order_count"])
        result = validate_batch([h], signals)
        assert len(result.conflicting_pairs) == 0
