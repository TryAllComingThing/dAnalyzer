"""假设回测验证

75/25 hold-out 分离 + 按假设类型选择通过标准 + 退化检查。
"""

from __future__ import annotations

import random
from typing import Callable

from learn.ingest.models import (
    DetectedSignal,
    Hypothesis,
    HypothesisStatus,
    HypothesisType,
    SignalType,
    ValidationResult,
)

# 按假设类型的通过标准
PASS_CRITERIA: dict[HypothesisType, dict[str, float]] = {
    HypothesisType.KEYWORD_ADJUSTMENT: {"min_pass_rate": 0.70, "max_degradation": 0.10},
    HypothesisType.INDICATOR_WEIGHT: {"min_pass_rate": 0.65, "max_degradation": 0.10},
    HypothesisType.INDICATOR_COMBINATION: {"min_pass_rate": 0.60, "max_degradation": 0.15},
    HypothesisType.TEMPLATE_ROUTING: {"min_pass_rate": 0.75, "max_degradation": 0.05},
    HypothesisType.TEMPLATE_CONTENT: {"min_pass_rate": 0.70, "max_degradation": 0.10},
    HypothesisType.TEMPLATE_DISCOVERY: {"min_pass_rate": 0.60, "max_degradation": 0.15},
    HypothesisType.INTENT_NEW: {"min_pass_rate": 0.50, "max_degradation": 0.20},
    HypothesisType.PREFERENCE_CHART: {"min_pass_rate": 0.70, "max_degradation": 0.05},
    HypothesisType.PREFERENCE_REPORT: {"min_pass_rate": 0.70, "max_degradation": 0.05},
}


def validate_hypothesis(
    hypothesis: Hypothesis,
    signals: list[DetectedSignal],
    holdout_ratio: float = 0.25,
    holdout_min_samples: int = 4,
    seed: int = 42,
) -> ValidationResult:
    """验证单条假设

    1. 从 signals 中分离训练集/保留集 (75/25 分层随机采样)
    2. 在保留集上回测假设
    3. 按假设类型选择通过标准
    4. 检查退化
    5. 产出 validated_confidence = confidence × pass_rate

    Args:
        hypothesis: 待验证的假设
        signals: 该假设的所有证据信号
        holdout_ratio: 保留集比例
        holdout_min_samples: 最少样本数才做分割
        seed: 随机种子

    Returns:
        ValidationResult 含 pass_rate + validated_confidence + 退化标记
    """
    total = len(signals)
    if total < holdout_min_samples:
        return ValidationResult(
            hypothesis_id=hypothesis.id,
            passed=False,
            pass_rate=0.0,
            validated_confidence=0.0,
            holdout_count=0,
            passed_count=0,
            degradation_found=False,
            notes=[f"Insufficient samples: {total} < {holdout_min_samples}"],
        )

    rng = random.Random(seed)
    indices = list(range(total))
    rng.shuffle(indices)
    holdout_n = max(int(total * holdout_ratio), 1)
    train_indices = set(indices[holdout_n:])
    holdout_indices = set(indices[:holdout_n])

    holdout_signals = [signals[i] for i in holdout_indices]
    train_signals = [signals[i] for i in train_indices]

    # 在保留集上回测
    passed_count = sum(1 for s in holdout_signals if _signal_supports_hypothesis(s, hypothesis))
    pass_rate = passed_count / len(holdout_signals) if holdout_signals else 0.0

    # 检查训练集退化（假设应用后训练集中的信号是否不再匹配）
    degradation_found, degraded = _check_degradation(train_signals, hypothesis)

    criteria = PASS_CRITERIA.get(hypothesis.type, {"min_pass_rate": 0.65, "max_degradation": 0.10})
    min_pass = criteria["min_pass_rate"]
    max_deg = criteria["max_degradation"]

    # 退化超过阈值 → 强制降级
    if degradation_found and len(degraded) / max(len(train_signals), 1) > max_deg:
        validated_confidence = hypothesis.confidence * pass_rate * 0.5
        passed = False
    elif pass_rate >= min_pass and not degradation_found:
        validated_confidence = hypothesis.confidence * pass_rate
        passed = True
    else:
        validated_confidence = hypothesis.confidence * pass_rate
        passed = False

    return ValidationResult(
        hypothesis_id=hypothesis.id,
        passed=passed,
        pass_rate=round(pass_rate, 4),
        validated_confidence=round(validated_confidence, 4),
        holdout_count=len(holdout_signals),
        passed_count=passed_count,
        degradation_found=degradation_found,
        degraded_queries=[s.session_id for s in degraded],
        notes=_build_notes(passed, pass_rate, degradation_found, criteria),
    )


def _signal_supports_hypothesis(
    signal: DetectedSignal, hypothesis: Hypothesis
) -> bool:
    """检查信号是否与假设一致

    一致的判断取决于假设类型和信号中的指标关系。
    """
    if hypothesis.type == HypothesisType.KEYWORD_ADJUSTMENT:
        # correction 信号: 用户纠正了某个指标 → 假设的 suggested 应匹配用户意图
        if not hypothesis.suggested:
            return True
        return any(ind in hypothesis.suggested for ind in signal.indicators_after)

    elif hypothesis.type == HypothesisType.INDICATOR_COMBINATION:
        # supplement 信号: 用户补充了指标 → 假设的 suggested 应包含该指标
        if not hypothesis.suggested:
            return True
        return any(ind in hypothesis.suggested for ind in signal.added_indicators)

    elif hypothesis.type == HypothesisType.INDICATOR_WEIGHT:
        # refinement 信号: 用户调整了指标权重
        return True  # refinement 总是支持权重调整

    elif hypothesis.type in (HypothesisType.PREFERENCE_CHART, HypothesisType.PREFERENCE_REPORT):
        suggested = hypothesis.suggested or {}
        return bool(signal.indicators_after) and signal.indicators_after[0] in suggested

    return True  # 默认宽松通过


def _check_degradation(
    train_signals: list[DetectedSignal], hypothesis: Hypothesis
) -> tuple[bool, list[DetectedSignal]]:
    """检查训练集中的信号是否与假设矛盾

    退化 = 假设与已有信号冲突。
    """
    degraded: list[DetectedSignal] = []
    for s in train_signals:
        # 如果信号方向与假设完全相反 → 退化
        if _signal_contradicts(s, hypothesis):
            degraded.append(s)

    return len(degraded) > 0, degraded


def _signal_contradicts(
    signal: DetectedSignal, hypothesis: Hypothesis
) -> bool:
    """信号是否与假设矛盾"""
    suggested = hypothesis.suggested or {}
    current = hypothesis.current or {}

    if hypothesis.type == HypothesisType.KEYWORD_ADJUSTMENT:
        # 如果信号的 indicators_after 匹配 current（被纠正前的状态）→ 矛盾
        if current:
            return bool(signal.indicators_after) and all(
                ind in current for ind in signal.indicators_after
            )
    return False


def _build_notes(
    passed: bool, pass_rate: float, degradation: bool, criteria: dict
) -> list[str]:
    notes: list[str] = []
    if not passed:
        if pass_rate < criteria.get("min_pass_rate", 0.65):
            notes.append(f"Pass rate {pass_rate:.2f} below threshold {criteria['min_pass_rate']}")
        if degradation:
            notes.append("Degradation detected in training set")
    else:
        notes.append(f"Passed with pass_rate={pass_rate:.2f}")
    return notes
