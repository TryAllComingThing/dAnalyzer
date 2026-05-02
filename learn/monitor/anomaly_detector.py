"""异常信号检测

检测知识投毒和异常用户行为：
- 单用户信号占比过高
- 24h 信号突发
- 权重异常
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from learn.ingest.models import DegradationResult, DetectedSignal, WindowMetrics


def check_single_user_dominance(
    signals: list[DetectedSignal],
    max_ratio: float = 0.50,
) -> bool:
    """检查单用户信号占比是否超过阈值

    Args:
        signals: 信号列表
        max_ratio: 单用户最大允许占比

    Returns:
        True 如果任一用户在信号群中占比 >= max_ratio
    """
    if not signals:
        return False

    total = len(signals)
    user_counts: dict[str, int] = {}
    for s in signals:
        uid = s.user_anon_id or "anonymous"
        user_counts[uid] = user_counts.get(uid, 0) + 1

    max_count = max(user_counts.values())
    return (max_count / total) >= max_ratio


def check_signal_burst(
    signals: list[DetectedSignal],
    window_hours: int = 24,
    burst_threshold: int = 10,
) -> bool:
    """检查是否存在信号突发

    同一 scenario + 同一信号类型在 window_hours 内超过 burst_threshold 条。

    Args:
        signals: 信号列表
        window_hours: 时间窗口（小时）
        burst_threshold: 突发阈值

    Returns:
        True 如果存在突发
    """
    if not signals:
        return False

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    # 按 (scenario, signal_type) 分组，统计窗口内数量
    groups: dict[tuple[str, str], int] = {}
    for s in signals:
        try:
            ts = datetime.fromisoformat(s.ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        if ts < window_start:
            continue
        key = (s.scenario, s.type.value)
        groups[key] = groups.get(key, 0) + 1

    return any(count >= burst_threshold for count in groups.values())


def check_weight_anomaly(
    current_weight: float,
    max_weight: float = 0.95,
) -> bool:
    """检查权重是否异常（超过最大允许值）

    Args:
        current_weight: 当前权重
        max_weight: 最大允许权重

    Returns:
        True 如果权重异常
    """
    return current_weight > max_weight


def check_degradation(
    window_metrics: WindowMetrics,
    user_dominance: bool = False,
    signal_burst: bool = False,
) -> DegradationResult:
    """综合退化判定

    结合窗口指标和异常检测标志，产出 DegradationResult。

    Args:
        window_metrics: 48h 窗口指标
        user_dominance: 是否存在单用户主导
        signal_burst: 是否存在信号突发

    Returns:
        DegradationResult 含 action 建议
    """
    degraded = False
    reasons: list[str] = []

    if not window_metrics.sufficient_samples:
        return DegradationResult(
            degraded=False,
            reason="insufficient_samples",
            window_metrics=window_metrics,
            action="none",
        )

    if window_metrics.l3_degradation:
        degraded = True
        reasons.append(f"l3_rate {window_metrics.l3_rate}% vs baseline {window_metrics.baseline_l3_rate}%")

    if window_metrics.correction_degradation:
        degraded = True
        reasons.append(f"correction_rate {window_metrics.correction_rate}% vs baseline {window_metrics.baseline_correction_rate}%")

    if user_dominance:
        degraded = True
        reasons.append("single_user_dominance")

    if signal_burst:
        degraded = True
        reasons.append("signal_burst")

    if not degraded:
        return DegradationResult(
            degraded=False,
            reason="all_metrics_stable",
            window_metrics=window_metrics,
            action="none",
        )

    # 判定 action
    action: Literal["freeze", "alert", "none"]
    if user_dominance or signal_burst:
        action = "alert"
    elif window_metrics.l3_degradation and window_metrics.correction_degradation:
        action = "freeze"
    else:
        action = "alert"

    return DegradationResult(
        degraded=True,
        reason="; ".join(reasons),
        window_metrics=window_metrics,
        action=action,
    )
