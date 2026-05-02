"""Phase 6 监控与异常检测单元测试

覆盖:
- health_metrics: 48h 窗口 + 周级报告
- anomaly_detector: 用户主导 / 信号突发 / 权重异常 / 退化判定
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from learn.ingest.models import (
    CounterRecord,
    DegradationResult,
    DetectedSignal,
    DetectionMethod,
    SignalType,
    WeeklyReport,
    WindowMetrics,
)
from learn.monitor.anomaly_detector import (
    check_degradation,
    check_signal_burst,
    check_single_user_dominance,
    check_weight_anomaly,
)
from learn.monitor.health_metrics import compute_48h_metrics, compute_weekly_report


def _make_counter(
    session: str = "s1",
    date: str = "2026-05-01",
    total_queries: int = 10,
    l1: int = 6,
    l2: int = 3,
    l3: int = 1,
    corrections: int = 1,
    supplements: int = 0,
    by_scenario: dict | None = None,
) -> CounterRecord:
    return CounterRecord(
        session=session,
        date=date,
        total_queries=total_queries,
        l1_hits=l1,
        l2_hits=l2,
        l3_fallbacks=l3,
        plan_validation_failures=0,
        corrections=corrections,
        supplements=supplements,
        refinements=0,
        errors=0,
        by_scenario=by_scenario or {},
    )


def _make_signal(
    stype: SignalType = SignalType.CORRECTION,
    session_id: str = "s1",
    scenario: str = "sales_trend",
    industry: str = "fmcg",
    user_anon_id: str = "",
    ts: str | None = None,
) -> DetectedSignal:
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat()
    return DetectedSignal(
        type=stype,
        session_id=session_id,
        turn_pair=(1, 2),
        industry=industry,
        scenario=scenario,
        ts=ts,
        user_anon_id=user_anon_id,
        detection_method=DetectionMethod.DISJOINT,
    )


# ============================================================
# Health Metrics 测试
# ============================================================


class Test48hMetrics:
    def test_basic_metrics(self):
        recent = [
            _make_counter(total_queries=20, l1=14, l3=2, corrections=2,
                          by_scenario={"sales_trend": {"correction": 2, "reinforcement": 10}}),
        ]
        baseline = [
            _make_counter(total_queries=20, l1=16, l3=1, corrections=1,
                          by_scenario={"sales_trend": {"correction": 1, "reinforcement": 8}}),
        ]

        m = compute_48h_metrics("sales_trend", recent, baseline)
        assert m.query_count >= 10
        assert m.l3_rate == 10.0
        assert m.l1_rate == 70.0
        assert m.baseline_l3_rate == 5.0

    def test_l3_degradation(self):
        recent = [
            _make_counter(total_queries=20, l1=10, l3=5, corrections=1,
                          by_scenario={"sales_trend": {"correction": 1, "reinforcement": 8}}),
        ]
        baseline = [
            _make_counter(total_queries=20, l1=15, l3=1, corrections=1,
                          by_scenario={"sales_trend": {"correction": 1, "reinforcement": 8}}),
        ]

        m = compute_48h_metrics("sales_trend", recent, baseline, min_samples=10)
        # l3_rate = 5/20 = 25%, baseline = 5% → diff = 20pp >= 5pp
        assert m.l3_degradation
        assert m.sufficient_samples

    def test_correction_degradation(self):
        recent = [
            _make_counter(total_queries=20, l1=12, l3=2, corrections=6,
                          by_scenario={"sales_trend": {"correction": 6, "reinforcement": 8}}),
        ]
        baseline = [
            _make_counter(total_queries=20, l1=14, l3=1, corrections=1,
                          by_scenario={"sales_trend": {"correction": 1, "reinforcement": 8}}),
        ]

        m = compute_48h_metrics("sales_trend", recent, baseline, min_samples=10)
        assert m.correction_degradation

    def test_insufficient_samples(self):
        recent = [
            _make_counter(total_queries=3, l1=1, l3=1, corrections=0,
                          by_scenario={"sales_trend": {"correction": 0}}),
        ]
        baseline = [
            _make_counter(total_queries=3, l1=2, l3=0, corrections=0,
                          by_scenario={"sales_trend": {"correction": 0}}),
        ]

        m = compute_48h_metrics("sales_trend", recent, baseline, min_samples=10)
        assert not m.sufficient_samples
        assert not m.l3_degradation
        assert not m.correction_degradation

    def test_empty_counters(self):
        m = compute_48h_metrics("sales_trend", [], [], min_samples=10)
        assert m.query_count == 0
        assert m.l3_rate == 0.0
        assert m.l1_rate == 0.0
        assert not m.sufficient_samples


class TestWeeklyReport:
    def test_healthy(self):
        counters = [
            _make_counter(total_queries=20, l3=2, corrections=1, supplements=1,
                          by_scenario={"sales_trend": {"reinforcement": 8, "counterfactual": 2}}),
        ]
        r = compute_weekly_report("2026-05-01", counters, total_patches=4, frozen_patches=0,
                                   total_drafts=2, promoted_drafts=1)
        assert r.health_status == "healthy"
        assert r.l3_rate == pytest.approx(0.10)
        assert r.total_queries == 20
        assert r.draft_promotion_rate == pytest.approx(0.50)

    def test_watch_on_elevated_l3(self):
        counters = [
            _make_counter(total_queries=20, l3=4, corrections=1, supplements=0,
                          by_scenario={"sales_trend": {"reinforcement": 4}}),
        ]
        r = compute_weekly_report("2026-05-01", counters)
        assert r.health_status == "watch"

    def test_degrading_on_high_l3(self):
        counters = [
            _make_counter(total_queries=20, l3=6, corrections=3, supplements=1,
                          by_scenario={"sales_trend": {"reinforcement": 1}}),
        ]
        r = compute_weekly_report("2026-05-01", counters)
        assert r.health_status == "degrading"

    def test_degrading_on_high_signal_efficiency(self):
        counters = [
            _make_counter(total_queries=20, l3=2, corrections=4, supplements=3,
                          by_scenario={"sales_trend": {"reinforcement": 4}}),
        ]
        r = compute_weekly_report("2026-05-01", counters)
        # signal_efficiency = (4+3)/20 = 0.35 → > 0.20 → degrading
        assert r.health_status == "degrading"

    def test_watch_on_high_freeze_rate(self):
        counters = [
            _make_counter(total_queries=20, l3=3, corrections=1, supplements=0,
                          by_scenario={"sales_trend": {"reinforcement": 4}}),
        ]
        r = compute_weekly_report("2026-05-01", counters, total_patches=10, frozen_patches=5)
        assert r.health_status == "watch"

    def test_zero_queries(self):
        r = compute_weekly_report("2026-05-01", [])
        assert r.total_queries == 0
        assert r.signal_efficiency == 0.0
        assert r.health_status == "healthy"


# ============================================================
# Anomaly Detector 测试
# ============================================================


class TestSingleUserDominance:
    def test_triggered_when_user_exceeds_max_ratio(self):
        signals = [
            _make_signal(user_anon_id="user_a") for _ in range(6)
        ] + [
            _make_signal(user_anon_id="user_b") for _ in range(4)
        ]
        assert check_single_user_dominance(signals, max_ratio=0.50)

    def test_not_triggered_when_below_ratio(self):
        signals = [
            _make_signal(user_anon_id="user_a") for _ in range(4)
        ] + [
            _make_signal(user_anon_id="user_b") for _ in range(3)
        ] + [
            _make_signal(user_anon_id="user_c") for _ in range(3)
        ]
        assert not check_single_user_dominance(signals, max_ratio=0.50)

    def test_empty_signals(self):
        assert not check_single_user_dominance([], max_ratio=0.50)

    def test_anonymous_users_grouped(self):
        signals = [_make_signal(user_anon_id="") for _ in range(5)]
        assert check_single_user_dominance(signals, max_ratio=0.50)


class TestSignalBurst:
    def test_triggered_when_group_exceeds_threshold(self):
        now = datetime.now(timezone.utc)
        signals = []
        for i in range(12):
            ts = (now - timedelta(hours=i)).isoformat()
            signals.append(_make_signal(
                stype=SignalType.CORRECTION, scenario="sales_trend", ts=ts,
            ))
        assert check_signal_burst(signals, window_hours=24, burst_threshold=10)

    def test_not_triggered_below_threshold(self):
        now = datetime.now(timezone.utc)
        signals = [
            _make_signal(
                stype=SignalType.CORRECTION, scenario="sales_trend",
                ts=(now - timedelta(hours=i)).isoformat(),
            )
            for i in range(5)
        ]
        assert not check_signal_burst(signals, window_hours=24, burst_threshold=10)

    def test_different_scenarios_separate(self):
        now = datetime.now(timezone.utc)
        signals = []
        for i in range(6):
            signals.append(_make_signal(
                stype=SignalType.CORRECTION, scenario="sales_trend",
                ts=(now - timedelta(hours=i)).isoformat(),
            ))
        for i in range(6):
            signals.append(_make_signal(
                stype=SignalType.CORRECTION, scenario="category_analysis",
                ts=(now - timedelta(hours=i)).isoformat(),
            ))
        assert not check_signal_burst(signals, window_hours=24, burst_threshold=10)

    def test_outside_window_excluded(self):
        now = datetime.now(timezone.utc)
        signals = [
            _make_signal(
                stype=SignalType.CORRECTION, scenario="sales_trend",
                ts=(now - timedelta(hours=30)).isoformat(),
            )
            for _ in range(12)
        ]
        assert not check_signal_burst(signals, window_hours=24, burst_threshold=10)

    def test_empty_signals(self):
        assert not check_signal_burst([], window_hours=24, burst_threshold=10)


class TestWeightAnomaly:
    def test_triggered_above_max(self):
        assert check_weight_anomaly(0.96, max_weight=0.95)

    def test_not_triggered_at_or_below_max(self):
        assert not check_weight_anomaly(0.95, max_weight=0.95)
        assert not check_weight_anomaly(0.50, max_weight=0.95)


class TestCheckDegradation:
    def test_insufficient_samples_returns_none(self):
        wm = WindowMetrics(
            scenario="sales_trend", query_count=5, l3_rate=5.0, l1_rate=70.0,
            correction_rate=2.0, baseline_l3_rate=2.0, baseline_correction_rate=1.0,
            l3_degradation=False, correction_degradation=False, sufficient_samples=False,
        )
        result = check_degradation(wm)
        assert not result.degraded
        assert result.reason == "insufficient_samples"
        assert result.action == "none"

    def test_freeze_when_both_degraded(self):
        wm = WindowMetrics(
            scenario="sales_trend", query_count=20, l3_rate=15.0, l1_rate=60.0,
            correction_rate=10.0, baseline_l3_rate=2.0, baseline_correction_rate=1.0,
            l3_degradation=True, correction_degradation=True, sufficient_samples=True,
        )
        result = check_degradation(wm)
        assert result.degraded
        assert result.action == "freeze"

    def test_alert_on_user_dominance(self):
        wm = WindowMetrics(
            scenario="sales_trend", query_count=20, l3_rate=3.0, l1_rate=70.0,
            correction_rate=2.0, baseline_l3_rate=2.0, baseline_correction_rate=1.0,
            l3_degradation=False, correction_degradation=False, sufficient_samples=True,
        )
        result = check_degradation(wm, user_dominance=True)
        assert result.degraded
        assert result.action == "alert"

    def test_alert_on_signal_burst(self):
        wm = WindowMetrics(
            scenario="sales_trend", query_count=20, l3_rate=3.0, l1_rate=70.0,
            correction_rate=2.0, baseline_l3_rate=2.0, baseline_correction_rate=1.0,
            l3_degradation=False, correction_degradation=False, sufficient_samples=True,
        )
        result = check_degradation(wm, signal_burst=True)
        assert result.degraded
        assert result.action == "alert"

    def test_stable_no_degradation(self):
        wm = WindowMetrics(
            scenario="sales_trend", query_count=20, l3_rate=3.0, l1_rate=70.0,
            correction_rate=2.0, baseline_l3_rate=3.0, baseline_correction_rate=2.0,
            l3_degradation=False, correction_degradation=False, sufficient_samples=True,
        )
        result = check_degradation(wm)
        assert not result.degraded
        assert result.action == "none"
        assert result.reason == "all_metrics_stable"
