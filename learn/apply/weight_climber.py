"""权重爬坡评估器

每周一 9am 执行。评估所有 progressive 状态假设的健康状况，
决定爬坡/冻结/衰减/废弃。
"""

from __future__ import annotations

from learn.ingest.models import ClimbResult, CounterRecord, Hypothesis, HypothesisStatus

# 渐进式权重参数
INITIAL_WEIGHT: float = 0.30
WEEKLY_CLIMB: float = 0.15
MAX_WEIGHT: float = 0.95
FREEZE_AFTER_WEEKS: int = 3
DECAY_AFTER_WEEKS: int = 8
DECAY_RATE: float = 0.05
MATURE_THRESHOLD: float = 0.80


def evaluate_climb(
    hypothesis: Hypothesis,
    recent_counters: list[CounterRecord],
    weeks_active: int,
    weeks_frozen: int = 0,
    current_weight: float | None = None,
) -> ClimbResult:
    """评估单条假设本周的爬坡状态

    Args:
        hypothesis: 当前假设
        recent_counters: 本周内的计数器（用于健康检查）
        weeks_active: 已激活周数
        weeks_frozen: 已冻结周数
        current_weight: 当前权重（默认从 INITIAL_WEIGHT 开始）

    Returns:
        ClimbResult 含新权重 + 动作
    """
    weight = current_weight if current_weight is not None else INITIAL_WEIGHT
    threshold = hypothesis.validated_confidence or hypothesis.confidence

    # 已达成熟阈值 → mature
    if weight >= MATURE_THRESHOLD and weeks_active > 0:
        return ClimbResult(
            hypothesis_id=hypothesis.id,
            current_weight=weight,
            new_weight=weight,
            weeks_active=weeks_active,
            weeks_frozen=weeks_frozen,
            action="mature",
            reason=f"Weight {weight:.2f} >= mature threshold {MATURE_THRESHOLD}",
        )

    # 长期冻结超过 8 周 → defunct
    if weeks_frozen >= DECAY_AFTER_WEEKS:
        return ClimbResult(
            hypothesis_id=hypothesis.id,
            current_weight=weight,
            new_weight=weight,
            weeks_active=weeks_active,
            weeks_frozen=weeks_frozen,
            action="defunct",
            reason=f"Frozen for {weeks_frozen} weeks >= {DECAY_AFTER_WEEKS}",
        )

    # 连续冻结 ≥ 3 周但 < 8 周 → decay
    if weeks_frozen >= FREEZE_AFTER_WEEKS:
        new_weight = max(weight - DECAY_RATE, 0.01)
        return ClimbResult(
            hypothesis_id=hypothesis.id,
            current_weight=weight,
            new_weight=round(new_weight, 4),
            weeks_active=weeks_active,
            weeks_frozen=weeks_frozen,
            action="decay",
            reason=f"Frozen for {weeks_frozen} weeks, decaying from {weight:.2f}",
        )

    # 有退化信号 → freeze
    if _has_degradation(recent_counters, hypothesis):
        return ClimbResult(
            hypothesis_id=hypothesis.id,
            current_weight=weight,
            new_weight=weight,
            weeks_active=weeks_active,
            weeks_frozen=weeks_frozen + 1,
            action="freeze",
            reason="Degradation detected in recent counters",
        )

    # 无足够数据 → hold
    if not recent_counters or not _has_supporting_signals(recent_counters, hypothesis):
        return ClimbResult(
            hypothesis_id=hypothesis.id,
            current_weight=weight,
            new_weight=weight,
            weeks_active=weeks_active,
            weeks_frozen=weeks_frozen,
            action="hold",
            reason="No supporting signals in this period",
        )

    # 无退化且有支持信号 → climb
    new_weight = min(weight + WEEKLY_CLIMB, MAX_WEIGHT)
    return ClimbResult(
        hypothesis_id=hypothesis.id,
        current_weight=weight,
        new_weight=round(new_weight, 4),
        weeks_active=weeks_active + 1,
        weeks_frozen=0,
        action="climb",
        reason=f"Climbing from {weight:.2f} to {new_weight:.2f} (+{WEEKLY_CLIMB})",
    )


def batch_evaluate(
    hypotheses: list[Hypothesis],
    counters: list[CounterRecord],
    hypothesis_weights: dict[str, float] | None = None,
    hypothesis_weeks: dict[str, tuple[int, int]] | None = None,
) -> list[ClimbResult]:
    """批量评估所有 progressive 假设"""
    weights = hypothesis_weights or {}
    weeks_map = hypothesis_weeks or {}
    results: list[ClimbResult] = []

    for h in hypotheses:
        if h.status != HypothesisStatus.PROGRESSIVE:
            continue
        active, frozen = weeks_map.get(h.id, (0, 0))
        cur_weight = weights.get(h.id, INITIAL_WEIGHT)
        result = evaluate_climb(
            h, counters, weeks_active=active, weeks_frozen=frozen,
            current_weight=cur_weight,
        )
        results.append(result)

    return results


def _has_degradation(
    counters: list[CounterRecord], hypothesis: Hypothesis
) -> bool:
    """检查本周计数器是否显示退化

    退化指标：L3 fallback 增多、correction 增多
    """
    if not counters:
        return False

    for c in counters:
        # 检查对应 scenario 的信号
        scenario_stats = c.by_scenario.get(hypothesis.evidence.signal_type.value if hypothesis.evidence else "", {})
        if not scenario_stats:
            # 尝试用 evidence 的 scenario 查找
            pass

        # L3 fallback 出现 → 退化
        if c.l3_fallbacks > 0:
            return True

    return False


def _has_supporting_signals(
    counters: list[CounterRecord], hypothesis: Hypothesis
) -> bool:
    """检查本周是否有支持信号（reinforcement / counterfactual hit）"""
    if not counters:
        return False

    total_queries = sum(c.total_queries for c in counters)

    # 有查询活动即可视为有信号
    return total_queries > 0
