"""置信度计算引擎

四维公式：频次(α=0.35) + 一致性(β=0.30) + 多样性(γ=0.20) + 邻近加分(δ=0.15)
"""

from __future__ import annotations

from collections import Counter
from math import sqrt

from learn.ingest.models import ConfidenceBreakdown, DetectedSignal, SignalType

# 分信号类型的频次饱和阈值
FREQUENCY_SAT: dict[SignalType, int] = {
    SignalType.CORRECTION: 5,
    SignalType.SUPPLEMENT: 5,
    SignalType.REFINEMENT: 5,
    SignalType.EXTENSION: 8,
    SignalType.L3_FALLBACK: 3,
}
FREQUENCY_SAT_DEFAULT: int = 5
DIVERSITY_SAT: int = 3


def get_frequency_sat(signal_type: SignalType) -> int:
    """按信号类型返回饱和阈值"""
    return FREQUENCY_SAT.get(signal_type, FREQUENCY_SAT_DEFAULT)


def calculate_frequency_score(frequency: int, signal_type: SignalType) -> float:
    """频次得分 = min(freq / F_sat, 1.0)"""
    sat = get_frequency_sat(signal_type)
    if sat <= 0:
        return 0.0
    return min(frequency / sat, 1.0)


def calculate_consistency_score(
    signals: list[DetectedSignal],
    user_decay_enabled: bool = True,
) -> float:
    """一致性得分：方向越集中越高。

    1. 按 direction key 分组（correction: before→after, supplement: added, etc.）
    2. 最大簇的信号数 / 总数 = 基础一致性
    3. 如果启用 user_decay，同用户在同方向的多条信号衰减为 sqrt(n)
    """
    if not signals:
        return 0.0

    groups: dict[str, list[DetectedSignal]] = {}
    for s in signals:
        key = _direction_key(s)
        groups.setdefault(key, []).append(s)

    if user_decay_enabled:
        total_weight = 0.0
        max_weight = 0.0
        for group_signals in groups.values():
            weight = _user_decayed_weight(group_signals)
            total_weight += weight
            if weight > max_weight:
                max_weight = weight
        if total_weight == 0:
            return 0.0
        return max_weight / total_weight
    else:
        counts = [len(g) for g in groups.values()]
        return max(counts) / len(signals)


def _user_decayed_weight(signals: list[DetectedSignal]) -> float:
    """对一组 signals 计算衰减加权后的有效权重

    同用户在同方向的多条信号衰减: w_u = 1/sqrt(n_user_signals)
    """
    user_counts: Counter[str] = Counter()
    for s in signals:
        uid = s.user_anon_id or "anon"
        user_counts[uid] += 1

    weight = 0.0
    for uid, count in user_counts.items():
        weight += 1.0 / sqrt(count)
    return weight


def _direction_key(signal: DetectedSignal) -> str:
    """为信号生成方向键，用于一致性分组"""
    before = ",".join(sorted(signal.indicators_before))
    after = ",".join(sorted(signal.indicators_after))
    return f"{signal.type.value}:{before}->{after}"


def calculate_diversity_score(unique_sessions: int) -> float:
    """多样性得分 = min(unique_sessions / D_sat, 1.0)"""
    if DIVERSITY_SAT <= 0:
        return 0.0
    return min(unique_sessions / DIVERSITY_SAT, 1.0)


def calculate_proximity_bonus(
    counterfactual_hits: int,
    total_signals: int,
) -> float:
    """反事实邻近加分：候选命中比例越高加分越大"""
    if total_signals <= 0:
        return 0.0
    return min(counterfactual_hits / total_signals, 1.0)


def calculate_confidence(
    signals: list[DetectedSignal],
    counterfactual_hits: int = 0,
    user_decay_enabled: bool = True,
    alpha: float = 0.35,
    beta: float = 0.30,
    gamma: float = 0.20,
    delta: float = 0.15,
) -> ConfidenceBreakdown:
    """综合计算四维置信度

    Args:
        signals: 属于同一个 cluster 的信号列表
        counterfactual_hits: 其中反事实命中的数量
        user_decay_enabled: 是否启用单用户衰减
        alpha, beta, gamma, delta: 四维权重

    Returns:
        ConfidenceBreakdown 含四维得分 + raw_confidence
    """
    if not signals:
        return ConfidenceBreakdown(
            frequency_score=0.0,
            consistency_score=0.0,
            diversity_score=0.0,
            proximity_bonus=0.0,
            raw_confidence=0.0,
            frequency_sat=0,
            diversity_sat=0,
        )

    signal_type = signals[0].type
    frequency = len(signals)
    unique_sessions = len({s.session_id for s in signals})

    freq_score = calculate_frequency_score(frequency, signal_type)
    cons_score = calculate_consistency_score(signals, user_decay_enabled)
    div_score = calculate_diversity_score(unique_sessions)
    prox_bonus = calculate_proximity_bonus(counterfactual_hits, frequency)

    raw = alpha * freq_score + beta * cons_score + gamma * div_score + delta * prox_bonus

    return ConfidenceBreakdown(
        frequency_score=round(freq_score, 4),
        consistency_score=round(cons_score, 4),
        diversity_score=round(div_score, 4),
        proximity_bonus=round(prox_bonus, 4),
        raw_confidence=round(raw, 4),
        frequency_sat=get_frequency_sat(signal_type),
        diversity_sat=DIVERSITY_SAT,
    )
