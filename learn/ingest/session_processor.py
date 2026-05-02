"""Session 处理器

Session 结束时的 Python 入口。加载 observation → 检测信号 → 写入 JSONL + counters。
由 learn/hooks/session-summary 调用。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from learn.ingest.counter_writer import append_signal, write_counters_jsonl
from learn.ingest.counterfactual_check import check_counterfactual
from learn.ingest.models import CounterRecord, DetectedSignal, Observation, SignalType
from learn.ingest.preference_detector import detect_preference
from learn.ingest.reinforcement_detector import detect_reinforcement
from learn.ingest.signal_detector import classify_query_pair, detect_extension

SIGNAL_FILE_MAP: dict[SignalType, str] = {
    SignalType.CORRECTION: "corrections",
    SignalType.SUPPLEMENT: "supplements",
    SignalType.REFINEMENT: "refinements",
    SignalType.EXTENSION: "extensions",
    SignalType.REINFORCEMENT: "reinforcements",
    SignalType.COUNTERFACTUAL: "counterfactuals",
    SignalType.PREFERENCE_CHART: "preferences",
    SignalType.PREFERENCE_REPORT: "preferences",
}


def process_session(
    session_id: str,
    observations: list[Observation],
    signals_dir: str | Path,
    counters_dir: str | Path,
    *,
    user_selections: dict[int, list[str]] | None = None,
    chart_choices: dict[int, tuple[str, str]] | None = None,
    report_choices: dict[int, tuple[str, str]] | None = None,
) -> tuple[list[DetectedSignal], CounterRecord]:
    """处理一个 session 的全部 observation。

    1. 遍历相邻 turns → classify_query_pair / detect_extension
    2. detect_reinforcement
    3. check_counterfactual（需要 user_selections）
    4. detect_preference（需要 chart/report choices）
    5. 原子写入信号 JSONL + 计数器

    Args:
        session_id: session 标识
        observations: 按 turn 排序的 observation 列表
        signals_dir: 信号 JSONL 输出目录
        counters_dir: 计数器 JSONL 输出目录
        user_selections: turn → 用户选择的指标列表（用于 counterfactual 检测）
        chart_choices: turn → (recommended_chart, selected_chart)
        report_choices: turn → (recommended_report, selected_report)
    """
    if not observations:
        return [], CounterRecord(session=session_id, date=_today())

    signals_dir = Path(signals_dir)
    counters_dir = Path(counters_dir)
    user_selections = user_selections or {}
    chart_choices = chart_choices or {}
    report_choices = report_choices or {}

    all_signals: list[DetectedSignal] = []

    # 1. 相邻 turn 对比
    for i in range(len(observations) - 1):
        prev, curr = observations[i], observations[i + 1]
        signal = classify_query_pair(prev, curr)
        if signal is not None:
            signal = _with_session(signal, session_id)
            all_signals.append(signal)
            _write_signal(signals_dir, signal)

        ext = detect_extension(prev, curr)
        if ext is not None:
            ext = _with_session(ext, session_id)
            all_signals.append(ext)
            _write_signal(signals_dir, ext)

    # 2. 强化信号
    reinf = detect_reinforcement(observations)
    for r in reinf:
        r = _with_session(r, session_id)
        all_signals.append(r)
        _write_signal(signals_dir, r)

    # 3. 反事实信号
    for obs in observations:
        selected = user_selections.get(obs.turn, [])
        if selected:
            result = check_counterfactual(obs, selected)
            if result is not None and result.candidate_hit:
                signal = DetectedSignal(
                    type=SignalType.COUNTERFACTUAL,
                    session_id=session_id,
                    turn_pair=(obs.turn, obs.turn),
                    industry=obs.industry,
                    scenario=obs.scenarios_retrieved[0] if obs.scenarios_retrieved else "",
                    indicators_before=result.indicators_retrieved,
                    indicators_after=result.user_selected,
                    query_before=obs.query,
                    candidate_hit=True,
                    hit_ranks=result.hit_ranks,
                    user_anon_id=obs.user_anon_id,
                )
                all_signals.append(signal)
                _write_signal(signals_dir, signal)

    # 4. 偏好信号
    for obs in observations:
        chart = chart_choices.get(obs.turn)
        report = report_choices.get(obs.turn)
        if chart or report:
            pref_signals = detect_preference(
                obs,
                user_chart_choice=chart[1] if chart else None,
                recommended_chart=chart[0] if chart else None,
                user_report_choice=report[1] if report else None,
                recommended_report=report[0] if report else None,
            )
            for ps in pref_signals:
                ps = _with_session(ps, session_id)
                all_signals.append(ps)
                _write_signal(signals_dir, ps)

    # 5. 聚合计数器
    counter = _aggregate_counters(session_id, observations, all_signals)

    # 写入计数器
    write_counters_jsonl(counters_dir, counter.date, counter)

    return all_signals, counter


def load_observations(session_path: str | Path) -> list[Observation]:
    """从 JSONL 文件加载 observation 列表"""
    session_path = Path(session_path)
    if not session_path.exists():
        return []

    observations: list[Observation] = []
    for line in session_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                obs = _parse_observation(json.loads(line))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
            observations.append(obs)
    return observations


def _write_signal(signals_dir: Path, signal: DetectedSignal) -> None:
    file_name = SIGNAL_FILE_MAP.get(signal.type, "unknown")
    file_path = signals_dir / f"{file_name}.jsonl"
    append_signal(file_path, signal)


def _with_session(signal: DetectedSignal, session_id: str) -> DetectedSignal:
    return DetectedSignal(
        type=signal.type,
        session_id=session_id,
        turn_pair=signal.turn_pair,
        industry=signal.industry,
        scenario=signal.scenario,
        ts=signal.ts,
        indicators_before=signal.indicators_before,
        indicators_after=signal.indicators_after,
        template_before=signal.template_before,
        template_after=signal.template_after,
        query_before=signal.query_before,
        query_after=signal.query_after,
        detection_method=signal.detection_method,
        replacement_ratio=signal.replacement_ratio,
        replaced_indicators=signal.replaced_indicators,
        added_indicators=signal.added_indicators,
        kept_indicators=signal.kept_indicators,
        candidate_hit=signal.candidate_hit,
        hit_ranks=signal.hit_ranks,
        user_anon_id=signal.user_anon_id,
    )


def _aggregate_counters(
    session_id: str,
    observations: list[Observation],
    signals: list[DetectedSignal],
) -> CounterRecord:
    by_type = _count_by_type(signals)
    by_scenario: dict[str, dict[str, int]] = {}
    for sig in signals:
        if sig.scenario:
            bucket = by_scenario.setdefault(sig.scenario, {})
            bucket[sig.type.value] = bucket.get(sig.type.value, 0) + 1

    l1 = sum(1 for o in observations if o.source == "l1_exact")
    l3 = sum(1 for o in observations if o.source == "l3_fallback")
    l2 = len(observations) - l1 - l3

    return CounterRecord(
        session=session_id,
        date=_today(),
        total_queries=len(observations),
        l1_hits=l1,
        l2_hits=l2,
        l3_fallbacks=l3,
        corrections=by_type.get(SignalType.CORRECTION, 0),
        supplements=by_type.get(SignalType.SUPPLEMENT, 0),
        refinements=by_type.get(SignalType.REFINEMENT, 0),
        errors=sum(1 for o in observations if o.error),
        by_scenario=by_scenario,
    )


def _count_by_type(signals: list[DetectedSignal]) -> dict[SignalType, int]:
    counts: dict[SignalType, int] = {}
    for s in signals:
        counts[s.type] = counts.get(s.type, 0) + 1
    return counts


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _parse_observation(d: dict) -> Observation:
    """从 dict 还原 Observation（不含 context/Candidate 深度嵌套）"""
    from learn.ingest.models import Candidate, ObservationContext, TimePeriod, TriggerSource

    ctx = d.get("context", {})
    context = ObservationContext(
        time_period=TimePeriod(ctx.get("time_period", "normal")),
        query_raw=ctx.get("query_raw", ""),
        trigger_source=TriggerSource(ctx.get("trigger_source", "new_query")),
        query_intent_hint=ctx.get("query_intent_hint"),
    )
    candidates = [
        Candidate(id=c["id"], score=c["score"], rank=c["rank"])
        for c in d.get("indicators_candidates", [])
    ]

    return Observation(
        turn=d["turn"],
        query=d["query"],
        industry=d["industry"],
        indicators_retrieved=d.get("indicators_retrieved", []),
        scenarios_retrieved=d.get("scenarios_retrieved", []),
        context=context,
        source=d.get("source", "l2_match"),
        indicators_candidates=candidates,
        models_retrieved=d.get("models_retrieved", []),
        analysis_type=d.get("analysis_type", ""),
        skill_chain_planned=d.get("skill_chain_planned", []),
        skill_chain_actual=d.get("skill_chain_actual", []),
        template_matched=d.get("template_matched"),
        user_anon_id=d.get("user_anon_id", ""),
        error=d.get("error"),
    )
