"""模板偏离监控

统计模板中指标/步骤的被接受/替换/跳过/补充频率，
检测触发条件产生 DeviationReport。
"""

from __future__ import annotations

from collections import defaultdict

from learn.ingest.models import (
    DetectedSignal,
    DeviationReport,
    DraftTemplate,
    SignalType,
)

# 触发阈值
SKIP_DEMOTE_THRESHOLD: float = 0.50     # 跳过率 >= 50% → 降级
SUPPLEMENT_ADD_THRESHOLD: float = 0.35   # 补充率 >= 35% → 加入
STEP_SKIP_THRESHOLD: float = 0.60        # 步骤跳过率 >= 60% → optional


def compute_deviation(
    template: DraftTemplate,
    signals: list[DetectedSignal],
    weeks: int = 4,
    min_usage: int = 5,
) -> DeviationReport:
    """计算模板偏离度

    Args:
        template: 目标模板
        signals: 与该模板相关的信号（按 template_matched 筛选）
        weeks: 统计周期（周）
        min_usage: 最少使用次数才触发分析

    Returns:
        DeviationReport 含指标/步骤统计 + 触发建议列表
    """
    indicator_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"accepted": 0, "replaced": 0, "skipped": 0, "supplemented": 0}
    )
    step_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"executed": 0, "skipped": 0, "supplemented": 0}
    )

    # 从模板提取所有指标
    template_indicators: set[str] = set()
    for item in template.indicators.values():
        assert isinstance(item, list)
        for entry in item:
            if isinstance(entry, dict):
                name: str = str(entry.get("id", entry.get("name", "")))
                if name:
                    template_indicators.add(name)

    usage_count = 0
    for signal in signals:
        usage_count += 1

        if signal.type == SignalType.REINFORCEMENT:
            # 用户接受 → 模板中已返回的指标计为 accepted
            for ind in signal.indicators_before:
                if ind in template_indicators:
                    indicator_stats[ind]["accepted"] += 1

        elif signal.type == SignalType.CORRECTION:
            # 用户纠正 → replaced 指标 + 新指标
            for ind in signal.replaced_indicators:
                if ind in template_indicators:
                    indicator_stats[ind]["replaced"] += 1
            # 新指标不在模板中 → 可能需要加入
            for ind in signal.indicators_after:
                if ind not in template_indicators:
                    indicator_stats[ind]["supplemented"] += 1

        elif signal.type == SignalType.SUPPLEMENT:
            # 补充指标
            for ind in signal.added_indicators:
                indicator_stats[ind]["supplemented"] += 1

        elif signal.type == SignalType.REFINEMENT:
            # 调整：替换的 → replaced, 新增的 → supplemented
            for ind in signal.replaced_indicators:
                if ind in template_indicators:
                    indicator_stats[ind]["replaced"] += 1
            for ind in signal.added_indicators:
                if ind not in template_indicators:
                    indicator_stats[ind]["supplemented"] += 1

        elif signal.type == SignalType.EXTENSION:
            # 扩展步骤
            for ind in signal.indicators_after:
                if ind not in template_indicators and ind:
                    indicator_stats.setdefault(ind, {})["supplemented"] += 1

    # 触发条件检测
    triggers: list[str] = []

    if usage_count >= min_usage:
        for ind, stats in indicator_stats.items():
            total = stats["accepted"] + stats["replaced"]
            if total > 0:
                skip_rate = stats["replaced"] / total
                if skip_rate >= SKIP_DEMOTE_THRESHOLD:
                    triggers.append(f"demote:{ind}")
            supplement_total = stats["supplemented"]
            if supplement_total / max(usage_count, 1) >= SUPPLEMENT_ADD_THRESHOLD:
                triggers.append(f"add:{ind}")

        for step, stats in step_stats.items():
            total_step = stats["executed"] + stats["skipped"]
            if total_step > 0 and stats["skipped"] / total_step >= STEP_SKIP_THRESHOLD:
                triggers.append(f"toggle_optional:{step}")

    return DeviationReport(
        template_id=template.id,
        weeks=weeks,
        usage_count=usage_count,
        indicator_stats=dict(indicator_stats),
        step_stats=dict(step_stats),
        triggers=triggers,
    )
