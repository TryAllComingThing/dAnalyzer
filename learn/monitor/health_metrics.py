"""健康度量计算

48h 快速窗口监控 + 周级健康趋势报告。
"""

from __future__ import annotations

from typing import Literal

from learn.ingest.models import CounterRecord, WeeklyReport, WindowMetrics


def compute_48h_metrics(
    scenario: str,
    recent_counters: list[CounterRecord],
    baseline_counters: list[CounterRecord],
    min_samples: int = 10,
    l3_pp_threshold: float = 5.0,
    correction_pp_threshold: float = 5.0,
) -> WindowMetrics:
    """计算 48h 窗口内的健康指标

    Args:
        scenario: 目标场景
        recent_counters: 最近 48h 的计数器
        baseline_counters: 历史基线计数器
        min_samples: 最少样本数才触发退化判定
        l3_pp_threshold: L3 率上升的百分点阈值
        correction_pp_threshold: 纠正率上升的百分点阈值

    Returns:
        WindowMetrics 含退化判定
    """
    query_count = 0
    l1_total = 0
    l3_total = 0
    corrections = 0

    for c in recent_counters:
        sb = c.by_scenario.get(scenario, {})
        query_count += sum(sb.values())
        l1_total += c.l1_hits
        l3_total += c.l3_fallbacks
        corrections += sb.get("correction", 0)

    total_queries = sum(c.total_queries for c in recent_counters)
    query_count = max(query_count, total_queries)

    baseline_l1 = 0
    baseline_l3 = 0
    baseline_total = 0
    baseline_corrections = 0
    for c in baseline_counters:
        sb = c.by_scenario.get(scenario, {})
        baseline_l1 += c.l1_hits
        baseline_l3 += c.l3_fallbacks
        baseline_total += c.total_queries
        baseline_corrections += sb.get("correction", 0)

    l3_rate = (l3_total / total_queries * 100) if total_queries > 0 else 0.0
    l1_rate = (l1_total / total_queries * 100) if total_queries > 0 else 0.0
    correction_rate = (corrections / query_count * 100) if query_count > 0 else 0.0

    baseline_l3_rate = (baseline_l3 / baseline_total * 100) if baseline_total > 0 else 0.0
    baseline_correction_rate = (baseline_corrections / baseline_total * 100) if baseline_total > 0 else 0.0

    sufficient_samples = query_count >= min_samples
    l3_degradation = sufficient_samples and (l3_rate - baseline_l3_rate) >= l3_pp_threshold
    correction_degradation = sufficient_samples and (correction_rate - baseline_correction_rate) >= correction_pp_threshold

    return WindowMetrics(
        scenario=scenario,
        query_count=query_count,
        l3_rate=round(l3_rate, 2),
        l1_rate=round(l1_rate, 2),
        correction_rate=round(correction_rate, 2),
        baseline_l3_rate=round(baseline_l3_rate, 2),
        baseline_correction_rate=round(baseline_correction_rate, 2),
        l3_degradation=l3_degradation,
        correction_degradation=correction_degradation,
        sufficient_samples=sufficient_samples,
    )


def compute_weekly_report(
    week_start: str,
    counters: list[CounterRecord],
    total_patches: int = 0,
    frozen_patches: int = 0,
    total_drafts: int = 0,
    promoted_drafts: int = 0,
) -> WeeklyReport:
    """生成周级健康报告

    Args:
        week_start: 周起始日期 (ISO 格式)
        counters: 本周所有计数器
        total_patches: 活跃补丁总数
        frozen_patches: 冻结补丁数
        total_drafts: 草稿模板总数
        promoted_drafts: 本周晋升的草稿数

    Returns:
        WeeklyReport 含健康状态判定
    """
    total_queries = sum(c.total_queries for c in counters)
    total_corrections = sum(c.corrections for c in counters)
    total_supplements = sum(c.supplements for c in counters)
    total_reinforcements = sum(
        sb.get("reinforcement", 0)
        for c in counters
        for sb in c.by_scenario.values()
    )
    total_counterfactuals = sum(
        sb.get("counterfactual", 0)
        for c in counters
        for sb in c.by_scenario.values()
    )
    l3_total = sum(c.l3_fallbacks for c in counters)

    signal_efficiency = (
        (total_corrections + total_supplements) / total_queries
        if total_queries > 0 else 0.0
    )
    reinforcement_rate = total_reinforcements / total_queries if total_queries > 0 else 0.0
    counterfactual_hit_rate = (
        total_counterfactuals / max(total_corrections, 1)
        if total_corrections > 0 else 0.0
    )
    l3_rate = l3_total / total_queries if total_queries > 0 else 0.0

    draft_promotion_rate = promoted_drafts / total_drafts if total_drafts > 0 else 0.0
    weight_freeze_rate = frozen_patches / total_patches if total_patches > 0 else 0.0

    # 健康判定
    health_status: Literal["healthy", "watch", "degrading"]
    if l3_rate > 0.25 or signal_efficiency > 0.20:
        health_status = "degrading"
    elif l3_rate > 0.15 or weight_freeze_rate > 0.30:
        health_status = "watch"
    else:
        health_status = "healthy"

    return WeeklyReport(
        week_start=week_start,
        total_queries=total_queries,
        signal_efficiency=round(signal_efficiency, 4),
        reinforcement_rate=round(reinforcement_rate, 4),
        counterfactual_hit_rate=round(counterfactual_hit_rate, 4),
        l3_rate=round(l3_rate, 4),
        draft_promotion_rate=round(draft_promotion_rate, 4),
        weight_freeze_rate=round(weight_freeze_rate, 4),
        health_status=health_status,
    )
