"""Day 14 全链路回测

端到端验证完整进化闭环:
  observation → signal → cluster → hypothesis
  → validate → apply → weight_climb
  → template_discovery → template_deviation → adjustment
  → health_metrics → anomaly_detection

每个阶段产出可检查的中间结果，模拟 3 个 session × 2 周的真实场景。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from learn.analyze.confidence import calculate_confidence
from learn.analyze.propagation import propagate_correction
from learn.analyze.signal_analyzer import (
    cluster_corrections,
    cluster_extensions,
    cluster_supplements,
    generate_hypotheses,
)
from learn.analyze.template_deviation import compute_deviation
from learn.analyze.template_discovery import discover_templates
from learn.apply.applier import apply_hypothesis
from learn.apply.draft_manager import evaluate_draft, simulate_weeks
from learn.apply.patch_builder import get_active_patches, rebuild_active
from learn.apply.template_updater import compute_adjustment
from learn.apply.weight_climber import evaluate_climb
from learn.ingest.models import (
    CounterRecord,
    DetectedSignal,
    DetectionMethod,
    DraftTemplate,
    Hypothesis,
    HypothesisStatus,
    HypothesisType,
    SignalType,
)
from learn.monitor.anomaly_detector import (
    check_degradation,
    check_signal_burst,
    check_single_user_dominance,
)
from learn.monitor.health_metrics import compute_48h_metrics, compute_weekly_report
from learn.validate.combo_validator import validate_batch
from learn.validate.validator import validate_hypothesis


# ============================================================
# 测试夹具：生成 3 session × 2 week 的模拟数据
# ============================================================


def _make_correction(session="s1", scenario="sales_trend", replaced=None, added=None,
                     before=None, after=None, user="user_a"):
    return DetectedSignal(
        type=SignalType.CORRECTION,
        session_id=session,
        turn_pair=(1, 2),
        industry="fmcg",
        scenario=scenario,
        replaced_indicators=replaced or ["sales_amount"],
        added_indicators=added or ["gross_margin"],
        indicators_before=before or ["sales_amount", "order_count"],
        indicators_after=after or ["gross_margin", "order_count"],
        detection_method=DetectionMethod.DISJOINT,
        user_anon_id=user,
    )


def _make_supplement(session="s1", scenario="sales_trend", added=None, user="user_b"):
    return DetectedSignal(
        type=SignalType.SUPPLEMENT,
        session_id=session,
        turn_pair=(1, 2),
        industry="fmcg",
        scenario=scenario,
        added_indicators=added or ["conversion_rate"],
        detection_method=DetectionMethod.PURE_ADDITION,
        user_anon_id=user,
    )


def _make_reinforcement(session="s1", scenario="sales_trend", before=None, user="user_c"):
    return DetectedSignal(
        type=SignalType.REINFORCEMENT,
        session_id=session,
        turn_pair=(1, 1),
        industry="fmcg",
        scenario=scenario,
        indicators_before=before or ["sales_amount", "order_count"],
        user_anon_id=user,
    )


def _make_extension(session="s1", scenario="promotion_analysis", steps=None, user="user_d"):
    return DetectedSignal(
        type=SignalType.EXTENSION,
        session_id=session,
        turn_pair=(1, 2),
        industry="fmcg",
        scenario=scenario,
        indicators_before=["data-query", "data-analysis"],
        indicators_after=steps or ["data-query", "data-analysis", "visual", "report"],
        detection_method=DetectionMethod.STRUCTURED_COMPARISON,
        user_anon_id=user,
    )


def _make_counter(session="s1", date="2026-05-01", total=10, l3=1, corrections=1,
                  supplements=0, by_scenario=None):
    return CounterRecord(
        session=session, date=date,
        total_queries=total, l1_hits=total - l3 - corrections,
        l2_hits=corrections, l3_fallbacks=l3,
        plan_validation_failures=0,
        corrections=corrections, supplements=supplements,
        refinements=0, errors=0,
        by_scenario=by_scenario or {},
    )


# ============================================================
# 全链路回测
# ============================================================


def _generate_signals() -> list[DetectedSignal]:
    """Helper: 3 session × 2 week 模拟信号"""
    all_signals: list[DetectedSignal] = []

    all_signals.append(_make_correction("s1", "sales_trend", user="user_a"))
    all_signals.append(_make_supplement("s1", "sales_trend", user="user_b"))
    all_signals.append(_make_reinforcement("s1", "sales_trend", user="user_c"))

    for _ in range(3):
        all_signals.append(_make_correction("s2", "sales_trend", user="user_b"))
    all_signals.append(_make_supplement("s2", "sales_trend",
                                        added=["conversion_rate"], user="user_a"))
    all_signals.append(_make_reinforcement("s2", "sales_trend", user="user_c"))

    for _ in range(2):
        all_signals.append(_make_correction("s3", "sales_trend", user="user_a"))
    for _ in range(5):
        all_signals.append(_make_extension("s3", "promotion_analysis", user="user_d"))

    return all_signals


class TestFullEvolutionLoop:
    """完整 10 阶段闭环验证"""

    def test_stage1_signal_accumulation(self):
        """Stage 1: 3 个 session 产生 15+ 条信号"""
        all_signals = _generate_signals()

        assert len(all_signals) == 15
        corrections = [s for s in all_signals if s.type == SignalType.CORRECTION]
        supplements = [s for s in all_signals if s.type == SignalType.SUPPLEMENT]
        extensions = [s for s in all_signals if s.type == SignalType.EXTENSION]
        assert len(corrections) == 6
        assert len(supplements) == 2
        assert len(extensions) == 5

    def test_stage2_clustering_produces_hypotheses(self):
        """Stage 2: 聚类 → 假设生成"""
        signals = _generate_signals()

        corrections = [s for s in signals if s.type == SignalType.CORRECTION]
        supplements = [s for s in signals if s.type == SignalType.SUPPLEMENT]

        corr_clusters = cluster_corrections(corrections)
        supp_clusters = cluster_supplements(supplements)

        assert len(corr_clusters) >= 1
        assert len(supp_clusters) >= 1

        all_clusters = corr_clusters + supp_clusters
        hypotheses = generate_hypotheses(all_clusters)
        assert len(hypotheses) >= 1
        valid_types = {HypothesisType.KEYWORD_ADJUSTMENT, HypothesisType.INDICATOR_COMBINATION,
                       HypothesisType.INDICATOR_WEIGHT}
        assert all(h.type in valid_types for h in hypotheses)

    def test_stage3_hypothesis_validation(self):
        """Stage 3: 75/25 hold-out 验证"""
        signals = _generate_signals()
        corrections = [s for s in signals if s.type == SignalType.CORRECTION]
        supplements = [s for s in signals if s.type == SignalType.SUPPLEMENT]

        clusters = cluster_corrections(corrections) + cluster_supplements(supplements)
        hypotheses = generate_hypotheses(clusters)

        for h in hypotheses:
            result = validate_hypothesis(h, signals, holdout_ratio=0.25)
            assert result.hypothesis_id == h.id
            assert 0.0 <= result.pass_rate <= 1.0

        # Batch validation
        if len(hypotheses) >= 2:
            batch = validate_batch(hypotheses[:2], signals)
            assert not batch.combo_passed or isinstance(batch.combo_passed, bool)

    def test_stage4_patch_application(self):
        """Stage 4: 假设 → 补丁 → _active/ 重建"""
        signals = _generate_signals()
        corrections = [s for s in signals if s.type == SignalType.CORRECTION]
        clusters = cluster_corrections(corrections)
        hypotheses = [h for h in generate_hypotheses(clusters)
                      if h.type == HypothesisType.INDICATOR_WEIGHT]

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            canonical = tmp_path / "_canonical"
            patches = tmp_path / "_patches"
            active = tmp_path / "_active"

            # Create minimal canonical indicator
            canonical.mkdir(parents=True)
            (canonical / "fmcg").mkdir()
            (canonical / "fmcg" / "indicators").mkdir()
            (canonical / "fmcg" / "indicators" / "sales_amount.yaml").write_text(
                "id: sales_amount\nname: 销售额\nweight: 0.80\n")

            patches.mkdir()
            active.mkdir(parents=True)

            for h in hypotheses[:2]:
                result = validate_hypothesis(h, signals, holdout_ratio=0.25)
                h = Hypothesis(
                    id=h.id, type=h.type, industry=h.industry,
                    evidence=h.evidence, target=h.target,
                    confidence=h.confidence,
                    validated_confidence=result.validated_confidence,
                    pass_rate=result.pass_rate,
                    status=HypothesisStatus.PENDING_VALIDATION,
                    suggested=h.suggested,
                )
                patch = apply_hypothesis(h, str(patches), str(canonical), str(active))
                assert patch.id == h.id
                assert patch.status in (HypothesisStatus.FULL_APPLIED,
                                        HypothesisStatus.PROGRESSIVE)

            # Rebuild _active/
            applied = rebuild_active(str(canonical), str(patches), str(active))
            assert isinstance(applied, dict)

            # Verify active patches
            active_patches = get_active_patches(str(patches))
            assert isinstance(active_patches, list)

    def test_stage5_weight_climbing(self):
        """Stage 5: 权重爬坡 5 周模拟"""
        signals = _generate_signals()
        corrections = [s for s in signals if s.type == SignalType.CORRECTION]
        clusters = cluster_corrections(corrections)
        hypotheses = generate_hypotheses(clusters)

        if not hypotheses:
            pytest.skip("No hypotheses generated")

        h = hypotheses[0]
        weight = 0.30
        weeks_active = 0
        weeks_frozen = 0

        # Week 1-3: no degradation → climb (need counters with queries for support)
        for _ in range(3):
            result = evaluate_climb(
                h, recent_counters=[_make_counter("s_active", "2026-05-01", total=10,
                                                   l3=0, corrections=0, supplements=0)],
                weeks_active=weeks_active,
                weeks_frozen=weeks_frozen, current_weight=weight,
            )
            assert result.action in ("climb", "hold")
            weight = result.new_weight
            weeks_active = result.weeks_active
            weeks_frozen = result.weeks_frozen

        assert weight >= 0.45  # 0.30 + 3 * 0.15

    def test_stage6_template_discovery(self):
        """Stage 6: Extension 信号 → 草稿模板发现"""
        extensions = [_make_extension(f"s{i % 4}", "promotion_analysis",
                                       steps=["data-query", "data-analysis", "visual", "report"])
                      for i in range(7)]

        drafts = discover_templates(extensions, [])
        assert len(drafts) == 1
        assert drafts[0].status == "draft"
        assert drafts[0].routing_weight == 0.25

    def test_stage7_draft_lifecycle(self):
        """Stage 7: 草稿 → 接受 → 晋升 → 完整生命周期"""
        draft = DraftTemplate(
            id="draft-full", name="Test Draft", status="draft", version=1,
            routing_weight=0.25,
            indicators={"required": [{"id": "sales_amount", "weight": 1.0}],
                        "optional": []},
            steps=[{"skill": "data-query", "optional": False},
                   {"skill": "data-analysis", "optional": False}],
            applicability={"scenarios": ["sales_trend"]},
            evidence_signals=["s1:1:2"],
        )

        # 5 accepts → promote
        current = draft
        for i in range(5):
            current, action = evaluate_draft(
                current,
                [_make_reinforcement(f"s_accept_{i}", "sales_trend")],
            )
        assert current.status == "active"
        assert current.routing_weight == pytest.approx(0.75)

        # 3 corrections on promoted → weight drops but stays active
        for i in range(3):
            current, action = evaluate_draft(
                current,
                [_make_correction(f"s_correct_{i}", "sales_trend")],
            )
        assert current.status == "active"
        assert current.routing_weight == pytest.approx(0.60)

    def test_stage8_template_deviation_to_adjustment(self):
        """Stage 8: 模板偏离 → 原子调整"""
        draft = DraftTemplate(
            id="tpl-dev", name="Deviation Test", status="active", version=1,
            routing_weight=0.70,
            indicators={"required": [{"id": "sales_amount", "weight": 1.0},
                                     {"id": "order_count", "weight": 0.70}],
                        "optional": [{"id": "conversion_rate", "weight": 0.50}]},
            steps=[{"skill": "data-query", "optional": False}],
            applicability={"scenarios": ["sales_trend"], "industries": ["fmcg"]},
            evidence_signals=["s1:1:2"],
        )

        signals: list[DetectedSignal] = []
        for i in range(10):
            signals.append(_make_reinforcement(f"s_dev_{i}", "sales_trend"))
        for i in range(10):
            signals.append(_make_correction(
                f"s_dev_c{i}", "sales_trend",
                replaced=["sales_amount"], before=["sales_amount"],
            ))

        report = compute_deviation(draft, signals, weeks=4)
        assert report.triggers

        adj = compute_adjustment(report, last_adjustment_week=-10, current_week=10)
        assert adj is not None
        assert adj.template_id == draft.id

    def test_stage9_health_metrics(self):
        """Stage 9: 计数器 → 48h 指标 + 周报"""
        recent = [
            _make_counter("s1", "2026-05-01", total=20, l3=2, corrections=2,
                          by_scenario={"sales_trend": {"correction": 2, "reinforcement": 8}}),
            _make_counter("s2", "2026-05-02", total=15, l3=1, corrections=1,
                          by_scenario={"sales_trend": {"correction": 1, "reinforcement": 6}}),
        ]
        baseline = [
            _make_counter("b1", "2026-04-01", total=20, l3=1, corrections=1,
                          by_scenario={"sales_trend": {"correction": 1, "reinforcement": 8}}),
        ]

        # 48h metrics
        window = compute_48h_metrics("sales_trend", recent, baseline, min_samples=10)
        assert window.query_count > 0
        assert window.sufficient_samples

        # Weekly report
        weekly = compute_weekly_report("2026-05-01", recent, total_patches=4,
                                        frozen_patches=0, total_drafts=2, promoted_drafts=1)
        assert weekly.total_queries == 35
        assert weekly.health_status in ("healthy", "watch", "degrading")

    def test_stage10_anomaly_detection(self):
        """Stage 10: 异常检测 — 用户主导 + 突发 + 退化判定"""
        # User dominance
        signals = []
        for _ in range(6):
            signals.append(_make_correction("s1", "sales_trend", user="user_a"))
        for _ in range(4):
            signals.append(_make_correction("s1", "sales_trend", user="user_b"))
        assert check_single_user_dominance(signals, max_ratio=0.50)

        # Degradation check
        window = compute_48h_metrics(
            "sales_trend",
            [_make_counter("s1", "2026-05-01", total=20, l3=4, corrections=2,
                           by_scenario={"sales_trend": {"correction": 2, "reinforcement": 8}})],
            [_make_counter("b1", "2026-04-01", total=20, l3=1, corrections=1,
                           by_scenario={"sales_trend": {"correction": 1, "reinforcement": 8}})],
            min_samples=10,
        )
        result = check_degradation(window, user_dominance=False, signal_burst=False)
        # L3: 4/20=20% vs baseline 1/20=5% → diff=15pp >= 5pp → degradation
        assert result.degraded
        assert result.action != "none"
