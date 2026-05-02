"""模板草稿发现

从 extension 信号中发现新的模板草稿。
通过四重门检查后自动生成 DraftTemplate。
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from learn.ingest.models import DetectedSignal, DraftTemplate, SignalType

# 四重门阈值
MIN_FREQUENCY: int = 5          # 最少出现次数
MIN_UNIQUE_SESSIONS: int = 3    # 最少跨 session 数
MIN_PATH_COMPLEXITY: int = 3    # 最少步骤复杂度


def discover_templates(
    extension_signals: list[DetectedSignal],
    existing_templates: list[DraftTemplate],
    min_frequency: int = MIN_FREQUENCY,
    min_unique_sessions: int = MIN_UNIQUE_SESSIONS,
    min_path_complexity: int = MIN_PATH_COMPLEXITY,
) -> list[DraftTemplate]:
    """从 extension 信号中发现新模板草稿

    四重门：
    1. 频次门：同一 skill_chain 扩展至少出现 min_frequency 次
    2. 跨 session 门：来自至少 min_unique_sessions 个不同 session
    3. 无现有匹配：不与已有模板 applicability 重叠
    4. 复杂度门：扩展路径包含 >= min_path_complexity 个步骤

    Args:
        extension_signals: 扩展信号列表
        existing_templates: 已有模板列表（用于去重）
        min_frequency: 最少频次
        min_unique_sessions: 最少跨 session
        min_path_complexity: 最少路径复杂度

    Returns:
        新草稿模板列表
    """
    extensions = [s for s in extension_signals if s.type == SignalType.EXTENSION]
    if not extensions:
        return []

    # 按 skill_chain 路径分组
    groups: dict[str, list[DetectedSignal]] = {}
    for s in extensions:
        key = _skill_chain_key(s)
        if key:
            groups.setdefault(key, []).append(s)

    existing_applicabilities = [_extract_applicability(t) for t in existing_templates]

    drafts: list[DraftTemplate] = []
    for path_key, sigs in groups.items():
        # 门 1: 频次
        if len(sigs) < min_frequency:
            continue

        # 门 2: 跨 session
        sessions = {s.session_id for s in sigs}
        if len(sessions) < min_unique_sessions:
            continue

        # 门 3: 无现有匹配
        if _matches_existing(path_key, existing_applicabilities):
            continue

        # 门 4: 复杂度
        steps = _extract_steps(sigs)
        if len(steps) < min_path_complexity:
            continue

        # 提取 indicators + applicability
        indicators = _extract_indicators_from_signals(sigs)
        applicability = _build_applicability(sigs)

        draft = DraftTemplate(
            id=_make_draft_id(path_key),
            name=_make_draft_name(sigs),
            status="draft",
            version=1,
            routing_weight=0.25,
            indicators={"required": indicators.get("required", []), "optional": indicators.get("optional", [])},
            steps=steps,
            applicability=applicability,
            evidence_signals=[f"{s.session_id}:{s.turn_pair}" for s in sigs],
            weeks_active=0,
        )
        drafts.append(draft)

    return drafts


def _skill_chain_key(signal: DetectedSignal) -> str:
    """为 extension 信号生成唯一的路径键"""
    after = signal.indicators_after if signal.indicators_after else []
    return "|".join(after) if after else ""


def _extract_steps(signals: list[DetectedSignal]) -> list[dict]:
    """从信号中提取步骤列表"""
    all_steps: list[str] = []
    seen: set[str] = set()
    for s in signals:
        for step in s.indicators_after:
            if step and step not in seen:
                all_steps.append(step)
                seen.add(step)
    return [{"skill": step, "optional": False} for step in all_steps]


def _extract_indicators_from_signals(
    signals: list[DetectedSignal],
) -> dict[str, list[dict]]:
    """从信号中提取指标信息"""
    indicators: set[str] = set()
    for s in signals:
        indicators.update(s.indicators_before)
        indicators.update(s.indicators_after)

    required = [{"id": ind, "weight": 0.50} for ind in sorted(indicators)[:10]]
    return {"required": required, "optional": []}


def _build_applicability(signals: list[DetectedSignal]) -> dict:
    """构建模板适用条件"""
    scenarios = {s.scenario for s in signals if s.scenario}
    industries = {s.industry for s in signals if s.industry}
    return {
        "scenarios": sorted(scenarios),
        "industries": sorted(industries),
        "min_turns": len(signals[0].indicators_after) if signals else 1,
    }


def _matches_existing(
    path_key: str, existing_applicabilities: list[dict]
) -> bool:
    """检查路径是否与已有模板重叠"""
    for app in existing_applicabilities:
        steps = app.get("steps", [])
        if not steps:
            continue
        existing_key = "|".join(steps)
        # 简单子串匹配
        if path_key in existing_key or existing_key in path_key:
            return True
    return False


def _extract_applicability(template: DraftTemplate) -> dict:
    """从模板提取 applicability + steps"""
    steps = [s.get("skill", "") for s in template.steps]
    result = dict(template.applicability)
    result["steps"] = steps
    return result


def _make_draft_id(path_key: str) -> str:
    return hashlib.sha256(path_key.encode()).hexdigest()[:12]


def _make_draft_name(signals: list[DetectedSignal]) -> str:
    scenario = signals[0].scenario if signals else "unknown"
    steps = [s.get("skill", "") for s in _extract_steps(signals)]
    return f"draft_{scenario}_{'_'.join(steps[:3])}"
