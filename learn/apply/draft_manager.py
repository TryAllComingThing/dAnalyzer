"""草稿模板生命周期管理

管理草稿模板的权重爬坡/衰减/晋升/废弃。
"""

from __future__ import annotations

from dataclasses import replace

from learn.ingest.models import DraftTemplate, DetectedSignal, SignalType

INITIAL_DRAFT_WEIGHT: float = 0.25
PROMOTION_THRESHOLD: float = 0.60
DEFUNCT_THRESHOLD: float = 0.30
DEFUNCT_AFTER_WEEKS: int = 12
CLEANUP_AFTER_WEEKS: int = 12

ACCEPT_DELTA: float = 0.10
CORRECT_DELTA: float = -0.05


def evaluate_draft(
    draft: DraftTemplate,
    signals: list[DetectedSignal],
    current_week: int | None = None,
) -> tuple[DraftTemplate, str]:
    """评估草稿模板的生命周期状态

    统计与草稿相关的信号，更新权重和状态。

    Args:
        draft: 草稿模板
        signals: 本期相关的信号
        current_week: 当前周号（用于状态转换判断）

    Returns:
        (updated_draft, action_description)
    """
    weight = draft.routing_weight
    acceptance_count = draft.acceptance_count
    rejection_count = draft.rejection_count
    weeks = draft.weeks_active + 1

    # 统计信号
    for signal in signals:
        if signal.type == SignalType.REINFORCEMENT:
            acceptance_count += 1
            weight = min(weight + ACCEPT_DELTA, 1.0)
        elif signal.type == SignalType.CORRECTION:
            rejection_count += 1
            weight = max(weight + CORRECT_DELTA, 0.01)
        # 其他信号类型不影响

    # 状态判定
    status = draft.status
    action = "hold"

    if weight >= PROMOTION_THRESHOLD:
        status = "active"
        action = "promote"
    elif weeks >= CLEANUP_AFTER_WEEKS:
        status = "defunct"
        action = "defunct_cleanup"
    elif weeks >= DEFUNCT_AFTER_WEEKS and weight < DEFUNCT_THRESHOLD:
        status = "defunct"
        action = "defunct"
    elif weight >= draft.routing_weight:
        action = "climb"
    elif weight < draft.routing_weight:
        action = "decay"

    updated = replace(
        draft,
        status=status,
        routing_weight=round(weight, 4),
        weeks_active=weeks,
        acceptance_count=acceptance_count,
        rejection_count=rejection_count,
    )

    return updated, action


def batch_evaluate_drafts(
    drafts: list[DraftTemplate],
    signals: list[DetectedSignal],
    current_week: int | None = None,
) -> list[tuple[DraftTemplate, str]]:
    """批量评估草稿模板"""
    results: list[tuple[DraftTemplate, str]] = []
    for draft in drafts:
        if draft.status != "active":
            updated, action = evaluate_draft(draft, signals, current_week)
            results.append((updated, action))
    return results


def simulate_weeks(
    draft: DraftTemplate,
    weekly_signals: list[list[DetectedSignal]],
) -> list[tuple[str, float]]:
    """模拟多周的草稿生命周期

    Args:
        draft: 草稿模板
        weekly_signals: 每周的信号列表

    Returns:
        [(status, weight), ...] 每周状态
    """
    history: list[tuple[str, float]] = []
    current = draft
    for week, sigs in enumerate(weekly_signals):
        current, action = evaluate_draft(current, sigs, current_week=week)
        history.append((action, current.routing_weight))
    return history
