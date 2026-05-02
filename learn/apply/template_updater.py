"""模板内容原子调整

从 DeviationReport 产出一条最高优先级调整。
调整后 4 周冷却期内不产出新调整。
"""

from __future__ import annotations

from learn.ingest.models import DeviationReport, TemplateAdjustment

# 调整类型优先级（数值越小越高）
PRIORITY: dict[str, int] = {
    "add_indicator": 0,
    "demote_indicator": 1,
    "toggle_optional": 2,
    "add_optional_step": 3,
    "promote_indicator": 4,
    "defunct": 5,
}

COOLDOWN_WEEKS: int = 4


def compute_adjustment(
    deviation: DeviationReport,
    last_adjustment_week: int = -COOLDOWN_WEEKS,
    current_week: int = 0,
) -> TemplateAdjustment | None:
    """从偏离报告计算一条原子调整

    每次仅产出一条调整（按优先级排序）。
    冷却期内不产出新调整。

    Args:
        deviation: 偏离度报告
        last_adjustment_week: 最近一次调整所在的周号
        current_week: 当前周号

    Returns:
        TemplateAdjustment 或 None（无调整/冷却中）
    """
    if current_week - last_adjustment_week < COOLDOWN_WEEKS:
        return None

    if not deviation.triggers:
        return None

    candidates: list[TemplateAdjustment] = []
    for trigger in deviation.triggers:
        adj = _parse_trigger(trigger, deviation)
        if adj:
            candidates.append(adj)

    if not candidates:
        return None

    # 按优先级 + indicator 名排序，取最高优先级的一条
    candidates.sort(key=lambda a: (PRIORITY.get(a.adjustment_type, 99), a.target))
    return candidates[0]


def _parse_trigger(
    trigger: str, deviation: DeviationReport
) -> TemplateAdjustment | None:
    """解析触发字符串为 TemplateAdjustment

    格式: "demote:indicator_id" / "add:indicator_id" / "toggle_optional:step"
    """
    if not trigger or ":" not in trigger:
        return None

    action_type, target = trigger.split(":", 1)
    type_map = {
        "demote": ("demote_indicator", _demote_action(target, deviation)),
        "add": ("add_indicator", _add_action(target, deviation)),
        "toggle_optional": (
            "toggle_optional",
            {"optional": True, "reason": f"Step {target} skip rate > {int(STEP_SKIP_THRESHOLD * 100)}%"},
        ),
        "promote": ("promote_indicator", _promote_action(target)),
        "defunct": ("defunct", {"defunct": True}),
    }

    if action_type not in type_map:
        return None

    adj_type, action = type_map[action_type]
    return TemplateAdjustment(
        template_id=deviation.template_id,
        adjustment_type=adj_type,
        target=target,
        action=action,
        priority=PRIORITY.get(adj_type, 99),
        reason=f"Deviation trigger: {trigger} (weeks={deviation.weeks})",
    )


def _demote_action(indicator: str, deviation: DeviationReport) -> dict:
    stats = deviation.indicator_stats.get(indicator, {})
    total = stats.get("accepted", 0) + stats.get("replaced", 0)
    skip_rate = stats.get("replaced", 0) / max(total, 1)
    return {"action": "demote", "current_skip_rate": round(skip_rate, 2)}


def _add_action(indicator: str, deviation: DeviationReport) -> dict:
    stats = deviation.indicator_stats.get(indicator, {})
    supplement_total = stats.get("supplemented", 0)
    return {
        "action": "add_to_optional",
        "supplement_count": supplement_total,
        "usage_count": deviation.usage_count,
    }


def _promote_action(indicator: str) -> dict:
    return {"action": "promote_to_required"}


# Re-export threshold for use in _parse_trigger
STEP_SKIP_THRESHOLD = 0.60
