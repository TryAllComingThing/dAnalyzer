"""Phase 5 模板进化单元测试

覆盖:
- template_deviation: 偏离度计算
- template_updater: 原子调整 + 冷却期
- template_discovery: 草稿发现 + 四重门
- draft_manager: 草稿生命周期
"""

from __future__ import annotations

import pytest

from learn.analyze.template_deviation import compute_deviation
from learn.apply.template_updater import COOLDOWN_WEEKS, compute_adjustment
from learn.analyze.template_discovery import discover_templates
from learn.apply.draft_manager import evaluate_draft, simulate_weeks
from learn.ingest.models import (
    DetectedSignal,
    DetectionMethod,
    DeviationReport,
    DraftTemplate,
    SignalType,
    TemplateAdjustment,
)


def _make_draft_template(
    tid: str = "tpl-001",
    indicators: dict | None = None,
    status: str = "draft",
    weight: float = 0.25,
    weeks_active: int = 0,
    steps: list[dict] | None = None,
    applicability: dict | None = None,
) -> DraftTemplate:
    return DraftTemplate(
        id=tid,
        name=f"Test Template {tid}",
        status=status,
        version=1,
        routing_weight=weight,
        indicators=indicators or {
            "required": [{"id": "sales_amount", "weight": 1.0}, {"id": "order_count", "weight": 0.70}],
            "optional": [{"id": "gross_margin_rate", "weight": 0.50}],
        },
        steps=steps or [{"skill": "data-query", "optional": False}, {"skill": "data-analysis", "optional": False}],
        applicability=applicability or {"scenarios": ["category_analysis"], "industries": ["fmcg"]},
        evidence_signals=["s1:1:2"],
        weeks_active=weeks_active,
        acceptance_count=weeks_active * 2,
    )


# ============================================================
# Template Deviation 测试
# ============================================================

class TestTemplateDeviation:
    def test_indicator_high_skip_triggers_demote(self):
        tpl = _make_draft_template()
        # 10 条 reinforcement (accepted) + 10 条 correction (replaced) for sales_amount
        signals: list[DetectedSignal] = []
        for i in range(10):
            signals.append(DetectedSignal(
                type=SignalType.REINFORCEMENT, session_id=f"s{i}", turn_pair=(1, 1),
                industry="fmcg", scenario="category_analysis",
                indicators_before=["sales_amount", "order_count"],
            ))
        for i in range(10):
            signals.append(DetectedSignal(
                type=SignalType.CORRECTION, session_id=f"s_c{i}", turn_pair=(1, 2),
                industry="fmcg", scenario="category_analysis",
                indicators_before=["sales_amount"], indicators_after=["gross_margin_rate"],
                replaced_indicators=["sales_amount"],
                detection_method=DetectionMethod.DISJOINT,
            ))

        report = compute_deviation(tpl, signals, weeks=4)
        assert report.usage_count == 20
        # sales_amount: 10 accepted + 10 replaced = 50% skip → triggers demote
        assert any("demote:sales_amount" in t for t in report.triggers)

    def test_indicator_frequent_supplement_triggers_add(self):
        tpl = _make_draft_template()
        signals: list[DetectedSignal] = []
        for i in range(10):
            signals.append(DetectedSignal(
                type=SignalType.REINFORCEMENT, session_id=f"s{i}", turn_pair=(1, 1),
                industry="fmcg", scenario="category_analysis",
                indicators_before=["sales_amount"],
            ))
        for i in range(8):  # 8/20 = 40% → triggers add
            signals.append(DetectedSignal(
                type=SignalType.SUPPLEMENT, session_id=f"sup{i}", turn_pair=(1, 2),
                industry="fmcg", scenario="category_analysis",
                added_indicators=["inventory_turnover"],
                detection_method=DetectionMethod.PURE_ADDITION,
            ))

        report = compute_deviation(tpl, signals, weeks=4)
        assert any("add:inventory_turnover" in t for t in report.triggers)

    def test_below_min_usage_no_triggers(self):
        tpl = _make_draft_template()
        signals = [
            DetectedSignal(
                type=SignalType.CORRECTION, session_id="s1", turn_pair=(1, 2),
                industry="fmcg", scenario="category_analysis",
                replaced_indicators=["sales_amount"],
                detection_method=DetectionMethod.DISJOINT,
            ),
        ]
        report = compute_deviation(tpl, signals, weeks=4, min_usage=5)
        assert report.triggers == []

    def test_empty_signals_returns_empty_report(self):
        tpl = _make_draft_template()
        report = compute_deviation(tpl, [], weeks=4)
        assert report.usage_count == 0
        assert report.triggers == []


# ============================================================
# Template Updater 测试
# ============================================================

class TestTemplateUpdater:
    def test_add_higher_priority_than_demote(self):
        report = DeviationReport(
            template_id="tpl-001", weeks=4, usage_count=20,
            indicator_stats={
                "sales_amount": {"accepted": 10, "replaced": 10, "skipped": 0, "supplemented": 0},
                "inventory_turnover": {"accepted": 0, "replaced": 0, "skipped": 0, "supplemented": 8},
            },
            step_stats={},
            triggers=["demote:sales_amount", "add:inventory_turnover"],
        )
        adj = compute_adjustment(report, last_adjustment_week=-10, current_week=10)
        assert adj is not None
        assert adj.adjustment_type == "add_indicator"
        assert adj.target == "inventory_turnover"

    def test_cooldown_blocks_adjustment(self):
        report = DeviationReport(
            template_id="tpl-001", weeks=4, usage_count=20,
            indicator_stats={}, step_stats={},
            triggers=["demote:sales_amount"],
        )
        adj = compute_adjustment(report, last_adjustment_week=8, current_week=10)
        assert adj is None  # 2 weeks since last adjustment < 4

    def test_no_triggers_returns_none(self):
        report = DeviationReport(
            template_id="tpl-001", weeks=4, usage_count=20,
            indicator_stats={}, step_stats={}, triggers=[],
        )
        adj = compute_adjustment(report, last_adjustment_week=-10, current_week=10)
        assert adj is None

    def test_step_skip_triggers_optional(self):
        report = DeviationReport(
            template_id="tpl-001", weeks=4, usage_count=20,
            indicator_stats={},
            step_stats={"visual": {"executed": 3, "skipped": 7, "supplemented": 0}},
            triggers=["toggle_optional:visual"],
        )
        adj = compute_adjustment(report, last_adjustment_week=-10, current_week=10)
        assert adj is not None
        assert adj.adjustment_type == "toggle_optional"


# ============================================================
# Template Discovery 测试
# ============================================================

class TestTemplateDiscovery:
    def test_four_gates_pass_produces_draft(self):
        signals = []
        for i in range(7):
            signals.append(DetectedSignal(
                type=SignalType.EXTENSION, session_id=f"s{i % 4}",
                turn_pair=(1, 2), industry="fmcg", scenario="promotion_analysis",
                indicators_before=["data-query", "data-analysis"],
                indicators_after=["data-query", "data-analysis", "visual", "report"],
                detection_method=DetectionMethod.STRUCTURED_COMPARISON,
            ))

        drafts = discover_templates(signals, [])
        assert len(drafts) == 1
        assert drafts[0].status == "draft"
        assert drafts[0].routing_weight == 0.25

    def test_below_min_frequency_no_draft(self):
        signals = [
            DetectedSignal(
                type=SignalType.EXTENSION, session_id="s1", turn_pair=(1, 2),
                industry="fmcg", scenario="category_analysis",
                indicators_after=["data-query", "data-analysis", "visual"],
                detection_method=DetectionMethod.STRUCTURED_COMPARISON,
            ),
        ]
        drafts = discover_templates(signals, [], min_frequency=5)
        assert drafts == []

    def test_below_min_sessions_no_draft(self):
        signals = []
        for i in range(6):
            signals.append(DetectedSignal(
                type=SignalType.EXTENSION, session_id="same_session",
                turn_pair=(1, 2), industry="fmcg", scenario="category_analysis",
                indicators_after=["data-query", "data-analysis", "visual", "report"],
                detection_method=DetectionMethod.STRUCTURED_COMPARISON,
            ))
        drafts = discover_templates(signals, [], min_unique_sessions=3)
        assert drafts == []

    def test_below_complexity_no_draft(self):
        signals = []
        for i in range(6):
            signals.append(DetectedSignal(
                type=SignalType.EXTENSION, session_id=f"s{i % 4}",
                turn_pair=(1, 2), industry="fmcg", scenario="category_analysis",
                indicators_after=["data-query"],
                detection_method=DetectionMethod.STRUCTURED_COMPARISON,
            ))
        drafts = discover_templates(signals, [], min_path_complexity=3)
        assert drafts == []

    def test_existing_template_blocks_discovery(self):
        existing = _make_draft_template(
            tid="existing-001",
            indicators={"required": [], "optional": []},
            steps=[{"skill": "data-query", "optional": False},
                   {"skill": "data-analysis", "optional": False},
                   {"skill": "visual", "optional": False}],
            applicability={"scenarios": ["category_analysis"]},
        )

        signals = []
        for i in range(6):
            signals.append(DetectedSignal(
                type=SignalType.EXTENSION, session_id=f"s{i % 4}",
                turn_pair=(1, 2), industry="fmcg", scenario="category_analysis",
                indicators_after=["data-query", "data-analysis", "visual"],
                detection_method=DetectionMethod.STRUCTURED_COMPARISON,
            ))
        drafts = discover_templates(signals, [existing])
        assert drafts == []


# ============================================================
# Draft Manager 测试
# ============================================================

class TestDraftManager:
    def test_accept_increases_weight(self):
        draft = _make_draft_template(weight=0.25)
        signals = [DetectedSignal(
            type=SignalType.REINFORCEMENT, session_id="s1", turn_pair=(1, 1),
            industry="fmcg", scenario="category_analysis",
        )]
        updated, action = evaluate_draft(draft, signals)
        assert updated.routing_weight == 0.35
        assert action == "climb"

    def test_correction_decreases_weight(self):
        draft = _make_draft_template(weight=0.30)
        signals = [DetectedSignal(
            type=SignalType.CORRECTION, session_id="s1", turn_pair=(1, 2),
            industry="fmcg", scenario="category_analysis",
            detection_method=DetectionMethod.DISJOINT,
        )]
        updated, action = evaluate_draft(draft, signals)
        assert updated.routing_weight == 0.25

    def test_promote_when_above_threshold(self):
        draft = _make_draft_template(weight=0.55)
        signals = [DetectedSignal(
            type=SignalType.REINFORCEMENT, session_id="s1", turn_pair=(1, 1),
            industry="fmcg", scenario="category_analysis",
        )]
        updated, action = evaluate_draft(draft, signals)
        assert updated.status == "active"
        assert action == "promote"

    def test_defunct_after_extended_low_weight(self):
        draft = _make_draft_template(weight=0.15, weeks_active=12)
        signals: list[DetectedSignal] = []
        updated, action = evaluate_draft(draft, signals)
        assert updated.status == "defunct"
        assert action in ("defunct", "defunct_cleanup")

    def test_simulate_weeks_to_promotion(self):
        draft = _make_draft_template(weight=0.25)
        # Simulate 4 weeks of reinforcement
        weekly = []
        for w in range(4):
            weekly.append([DetectedSignal(
                type=SignalType.REINFORCEMENT, session_id=f"s{w}", turn_pair=(1, 1),
                industry="fmcg", scenario="category_analysis",
            )])
        history = simulate_weeks(draft, weekly)
        assert len(history) == 4
        # Should reach weight >= 0.55 after 4 accepts (0.25 + 0.40 = 0.65)
        final_weight = history[-1][1]
        assert final_weight >= 0.55

    def test_batch_only_evaluates_non_active(self):
        active = _make_draft_template("active-tpl", status="active", weight=0.70)
        draft = _make_draft_template("draft-tpl", status="draft", weight=0.25)
        signals = [DetectedSignal(
            type=SignalType.REINFORCEMENT, session_id="s1", turn_pair=(1, 1),
            industry="fmcg", scenario="category_analysis",
        )]
        from learn.apply.draft_manager import batch_evaluate_drafts
        results = batch_evaluate_drafts([active, draft], signals)
        assert len(results) == 1
        assert results[0][0].id == "draft-tpl"
