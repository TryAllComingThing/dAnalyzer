"""组合验证

批量假设应用前的交叉回测。检测多假设交互退化。
"""

from __future__ import annotations

from learn.ingest.models import (
    BatchValidationResult,
    DetectedSignal,
    Hypothesis,
    ValidationResult,
)
from learn.validate.validator import _signal_supports_hypothesis


def validate_batch(
    hypotheses: list[Hypothesis],
    signals: list[DetectedSignal],
) -> BatchValidationResult:
    """批量验证多条假设的组合效果

    1. 逐条单独验证
    2. 组合回测（全部假设同时检查）
    3. 组合退化 → 二分排查定位冲突对
    """
    if not hypotheses:
        return BatchValidationResult(
            all_passed=True,
            hypothesis_results=[],
            combo_passed=True,
            combo_degradation=False,
        )

    # 逐条验证
    from learn.validate.validator import validate_hypothesis

    individual_results = [
        validate_hypothesis(h, signals) for h in hypotheses
    ]

    # 组合回测
    combo_passed, combo_degradation = _check_combo(hypotheses, signals)

    # 二分排查冲突对
    conflicting_pairs = _find_conflicts(hypotheses, signals) if combo_degradation else []

    all_passed = all(r.passed for r in individual_results) and not combo_degradation

    return BatchValidationResult(
        all_passed=all_passed,
        hypothesis_results=individual_results,
        combo_passed=combo_passed,
        combo_degradation=combo_degradation,
        conflicting_pairs=conflicting_pairs,
    )


def _check_combo(
    hypotheses: list[Hypothesis], signals: list[DetectedSignal]
) -> tuple[bool, bool]:
    """检查组合应用是否产生退化

    组合退化 = 任意信号与任一假设矛盾，但单独验证时该假设是合格的。
    """
    if not signals or not hypotheses:
        return True, False

    # 对每条信号，检查是否所有假设都支持
    degradation_count = 0
    for s in signals:
        supports_any = any(_signal_supports_hypothesis(s, h) for h in hypotheses)
        contradicts_all = all(not _signal_supports_hypothesis(s, h) for h in hypotheses)
        if contradicts_all:
            degradation_count += 1

    total = len(signals)
    degradation_ratio = degradation_count / total if total > 0 else 0.0

    return degradation_ratio < 0.15, degradation_ratio >= 0.15


def _find_conflicts(
    hypotheses: list[Hypothesis], signals: list[DetectedSignal]
) -> list[tuple[str, str]]:
    """二分排查定位冲突对

    对每对假设，检查联合应用时是否比单独应用更差。
    """
    if len(hypotheses) <= 1:
        return []

    conflicts: list[tuple[str, str]] = []
    for i in range(len(hypotheses)):
        for j in range(i + 1, len(hypotheses)):
            hi, hj = hypotheses[i], hypotheses[j]
            # 检查 hi 和 hj 的 target 是否指向同一字段但方向相反
            if _are_conflicting(hi, hj):
                conflicts.append((hi.id, hj.id))
    return conflicts


def _are_conflicting(h1: Hypothesis, h2: Hypothesis) -> bool:
    """两条假设是否冲突

    冲突条件：修改同一 target 的同一 field，但 suggested 相互矛盾。
    """
    if h1.target.path != h2.target.path:
        return False
    if h1.target.field != h2.target.field:
        return False

    s1 = h1.suggested or {}
    s2 = h2.suggested or {}

    # 查找矛盾的指标方向
    for ind in set(s1.keys()) & set(s2.keys()):
        v1 = s1.get(ind, 0)
        v2 = s2.get(ind, 0)
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            if (v1 > 0 and v2 < 0) or (v1 < 0 and v2 > 0):
                return True
    return False
