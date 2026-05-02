"""Phase 5 模板自主进化集成测试

覆盖完整生命周期:
1. Extension 信号 → 模板发现 → 产出草稿
2. 草稿接受/纠正 → 权重爬坡 → 晋升为正式
3. 模板偏离 → 原子调整 → 应用
"""

from __future__ import annotations

import pytest

from learn.analyze.template_deviation import compute_deviation
from learn.analyze.template_discovery import discover_templates
from learn.apply.draft_manager import evaluate_draft
from learn.apply.template_updater import compute_adjustment
from learn.ingest.models import (
    DetectedSignal,
    DetectionMethod,
    DraftTemplate,
    SignalType,
)


def _make_draft(indicators=None, steps=None, applicability=None, weight=0.25, status="draft", weeks=0):
    return DraftTemplate(
        id="tpl-test",
        name="Test Draft",
        status=status,
        version=1,
        routing_weight=weight,
        indicators=indicators or {
            "required": [{"id": "sales_amount", "weight": 1.0}],
            "optional": [{"id": "conversion_rate", "weight": 0.50}],
        },
        steps=steps or [{"skill": "data-query", "optional": False},
                        {"skill": "data-analysis", "optional": False}],
        applicability=applicability or {"scenarios": ["sales_trend"], "industries": ["fmcg"]},
        evidence_signals=["s1:1:2"],
        weeks_active=weeks,
        acceptance_count=weeks * 2,
    )


def _make_extension(count=7, sessions=4, steps=None, scenario="promotion_analysis", industry="fmcg"):
    steps = steps or ["data-query", "data-analysis", "visual", "report"]
    signals = []
    for i in range(count):
        signals.append(DetectedSignal(
            type=SignalType.EXTENSION, session_id=f"s{i % sessions}",
            turn_pair=(1, 2), industry=industry, scenario=scenario,
            indicators_before=["data-query", "data-analysis"],
            indicators_after=steps,
            detection_method=DetectionMethod.STRUCTURED_COMPARISON,
        ))
    return signals


def _make_reinforcement(count=1, session_id="s_r", scenario="promotion_analysis", industry="fmcg"):
    return [DetectedSignal(
        type=SignalType.REINFORCEMENT, session_id=session_id, turn_pair=(1, 1),
        industry=industry, scenario=scenario,
    ) for _ in range(count)]


def _make_correction(session_id="s_c", scenario="promotion_analysis", industry="fmcg"):
    return [DetectedSignal(
        type=SignalType.CORRECTION, session_id=session_id, turn_pair=(1, 2),
        industry=industry, scenario=scenario,
        detection_method=DetectionMethod.DISJOINT,
    )]


# ============================================================
# 完整生命周期
# ============================================================


class TestTemplateDiscoveryToActive:
    """延伸信号 → 发现草稿 → 权重爬坡 → 晋升"""

    def test_extension_signals_produce_draft_template(self):
        signals = _make_extension(count=7, sessions=4)
        drafts = discover_templates(signals, [])
        assert len(drafts) == 1
        draft = drafts[0]
        assert draft.status == "draft"
        assert draft.routing_weight == 0.25
        assert len(draft.steps) == 4
        assert "promotion_analysis" in draft.applicability["scenarios"]

    def test_draft_climbs_and_promotes_with_accepts(self):
        draft = _make_draft(weight=0.25, status="draft")
        history: list[tuple[float, str]] = [(draft.routing_weight, draft.status)]

        current = draft
        for week in range(5):
            signals = _make_reinforcement(count=1, session_id=f"s_w{week}")
            current, action = evaluate_draft(current, signals)
            history.append((current.routing_weight, current.status))

        # After 5 accepts: 0.25 + 5*0.10 = 0.75 → promoted
        assert current.status == "active"
        final_weight = current.routing_weight
        assert final_weight >= 0.60

    def test_repeated_corrections_keep_draft_low(self):
        draft = _make_draft(weight=0.25, status="draft")

        current = draft
        for week in range(3):
            signals = _make_correction(session_id=f"s_c{week}")
            current, action = evaluate_draft(current, signals)

        # After 3 corrections: 0.25 + 3*(-0.05) = 0.10
        assert current.routing_weight <= 0.15
        assert current.status == "draft"

    def test_draft_defunct_after_prolonged_low_weight(self):
        draft = _make_draft(weight=0.15, status="draft", weeks=12)
        current, action = evaluate_draft(draft, [])
        assert current.status == "defunct"
        assert action in ("defunct", "defunct_cleanup")

    def test_five_accepts_promotes_draft(self):
        """模拟 5 次接受 → 晋升为正式 — 开发计划验收场景"""
        draft = _make_draft(weight=0.25, status="draft")

        current = draft
        for i in range(5):
            current, action = evaluate_draft(
                current,
                _make_reinforcement(count=1, session_id=f"s_accept_{i}"),
            )

        assert current.status == "active"
        # 0.25 + 5 * 0.10 = 0.75
        assert current.routing_weight == pytest.approx(0.75)


# ============================================================
# 偏离检测 → 原子调整
# ============================================================


class TestDeviationToAdjustment:
    """模板偏离 → 原子调整 → 应用"""

    def test_high_skip_produces_demote_adjustment(self):
        draft = _make_draft()
        signals: list[DetectedSignal] = []
        for i in range(10):
            signals.append(DetectedSignal(
                type=SignalType.REINFORCEMENT, session_id=f"s{i}", turn_pair=(1, 1),
                industry="fmcg", scenario="sales_trend",
                indicators_before=["sales_amount", "conversion_rate"],
            ))
        for i in range(10):
            signals.append(DetectedSignal(
                type=SignalType.CORRECTION, session_id=f"s_c{i}", turn_pair=(1, 2),
                industry="fmcg", scenario="sales_trend",
                indicators_before=["sales_amount"], indicators_after=["conversion_rate"],
                replaced_indicators=["sales_amount"],
                detection_method=DetectionMethod.DISJOINT,
            ))

        report = compute_deviation(draft, signals, weeks=4)
        assert any("demote:sales_amount" in t for t in report.triggers)

        adj = compute_adjustment(report, last_adjustment_week=-10, current_week=10)
        assert adj is not None
        assert adj.adjustment_type == "demote_indicator"
        assert adj.target == "sales_amount"

    def test_frequent_supplement_produces_add_adjustment(self):
        draft = _make_draft()
        signals: list[DetectedSignal] = []
        for i in range(10):
            signals.append(DetectedSignal(
                type=SignalType.REINFORCEMENT, session_id=f"s{i}", turn_pair=(1, 1),
                industry="fmcg", scenario="sales_trend",
                indicators_before=["sales_amount"],
            ))
        for i in range(8):
            signals.append(DetectedSignal(
                type=SignalType.SUPPLEMENT, session_id=f"sup{i}", turn_pair=(1, 2),
                industry="fmcg", scenario="sales_trend",
                added_indicators=["customer_retention_rate"],
                detection_method=DetectionMethod.PURE_ADDITION,
            ))

        report = compute_deviation(draft, signals, weeks=4)
        assert any("add:customer_retention_rate" in t for t in report.triggers)

        adj = compute_adjustment(report, last_adjustment_week=-10, current_week=10)
        assert adj is not None
        assert adj.adjustment_type == "add_indicator"

    def test_cooldown_prevents_rapid_adjustments(self):
        draft = _make_draft()
        signals: list[DetectedSignal] = []
        for i in range(10):
            signals.append(DetectedSignal(
                type=SignalType.REINFORCEMENT, session_id=f"s{i}", turn_pair=(1, 1),
                industry="fmcg", scenario="sales_trend",
                indicators_before=["sales_amount"],
            ))
        for i in range(10):
            signals.append(DetectedSignal(
                type=SignalType.CORRECTION, session_id=f"s_c{i}", turn_pair=(1, 2),
                industry="fmcg", scenario="sales_trend",
                replaced_indicators=["sales_amount"],
                detection_method=DetectionMethod.DISJOINT,
            ))

        report = compute_deviation(draft, signals, weeks=4)
        # Last adjustment was only 2 weeks ago — still in cooldown
        adj = compute_adjustment(report, last_adjustment_week=8, current_week=10)
        assert adj is None


# ============================================================
# 端到端: 发现 → 爬坡 → 偏离 → 调整
# ============================================================


class TestEndToEndTemplateLifecycle:
    """完整模板生命周期"""

    def test_discovery_to_promotion_via_weight_climb(self):
        """Extension 信号 → 发现草稿 → 5 次接受 → 晋升"""
        ext_signals = _make_extension(count=7, sessions=4, steps=["data-query", "data-analysis", "visual", "report"])
        drafts = discover_templates(ext_signals, [])
        assert len(drafts) == 1
        draft = drafts[0]
        assert draft.status == "draft"
        assert draft.routing_weight == 0.25

        current = draft
        for i in range(5):
            current, action = evaluate_draft(
                current,
                _make_reinforcement(count=1, session_id=f"s_life_{i}"),
            )
        assert current.status == "active"
        assert current.routing_weight == pytest.approx(0.75)

    def test_deviation_to_adjustment_on_business_template(self):
        """业务模板偏离 → 检测 → 原子调整（使用业务指标模板）"""
        draft = _make_draft()

        signals: list[DetectedSignal] = []
        for i in range(10):
            signals.append(DetectedSignal(
                type=SignalType.REINFORCEMENT, session_id=f"s_dev_{i}", turn_pair=(1, 1),
                industry="fmcg", scenario="sales_trend",
                indicators_before=["sales_amount", "conversion_rate"],
            ))
        for i in range(10):
            signals.append(DetectedSignal(
                type=SignalType.CORRECTION, session_id=f"s_dev_c{i}", turn_pair=(1, 2),
                industry="fmcg", scenario="sales_trend",
                replaced_indicators=["sales_amount"],
                detection_method=DetectionMethod.DISJOINT,
            ))

        report = compute_deviation(draft, signals, weeks=4)
        assert report.triggers

        adj = compute_adjustment(report, last_adjustment_week=-10, current_week=10)
        assert adj is not None
        assert adj.template_id == draft.id
        assert adj.adjustment_type in ("demote_indicator", "add_indicator")

    def test_no_discovery_when_existing_covers_scenario(self):
        existing = _make_draft(
            steps=[{"skill": "data-query", "optional": False},
                   {"skill": "data-analysis", "optional": False},
                   {"skill": "visual", "optional": False}],
            applicability={"scenarios": ["category_analysis"]},
        )
        signals = _make_extension(
            count=6, sessions=4,
            steps=["data-query", "data-analysis", "visual"],
            scenario="category_analysis",
        )
        drafts = discover_templates(signals, [existing])
        assert drafts == []

    def test_accept_and_correct_balance(self):
        """混合 accept + correct 场景：爬坡与衰减交错"""
        draft = _make_draft(weight=0.30, status="draft")

        # Week 1: accept → 0.40
        current, action = evaluate_draft(draft, _make_reinforcement(session_id="sw1"))
        assert current.routing_weight == pytest.approx(0.40)
        assert action == "climb"

        # Week 2: correct → 0.35
        current, action = evaluate_draft(current, _make_correction(session_id="sw2"))
        assert current.routing_weight == pytest.approx(0.35)

        # Week 3-7: 5 accepts → 0.35 + 0.50 = 0.85 → promote
        for i in range(5):
            current, action = evaluate_draft(
                current,
                _make_reinforcement(session_id=f"sw{i+3}"),
            )
        assert current.status == "active"
