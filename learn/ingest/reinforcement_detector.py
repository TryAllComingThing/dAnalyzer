"""强化信号检测器

检测用户接受系统推荐的行为。用户在收到结果后产生新查询（unrelated scenario）
或 session 结束 → 上一轮结果标记为 accepted。
"""

from __future__ import annotations

from learn.ingest.models import DetectedSignal, Observation, SignalType


def detect_reinforcement(
    session_observations: list[Observation],
) -> list[DetectedSignal]:
    """从 session 的 observation 序列中检测强化信号。

    规则:
    - Turn N 和 Turn N+1 的 scenario 不同 → Turn N 被接受
    - Session 最后一轮 → 被接受（session 结束时无后续纠正 = 接受）

    返回: 每轮最多产生 1 个 reinforcement 信号
    """
    if len(session_observations) < 2:
        return []

    signals: list[DetectedSignal] = []
    for i, obs in enumerate(session_observations[:-1]):
        next_obs = session_observations[i + 1]
        # 下一轮 scenario 变了 → 说明用户对当前结果满意，开启了新话题
        if set(obs.scenarios_retrieved) != set(next_obs.scenarios_retrieved):
            # 但下一轮不是纠正 → 当前轮被接受
            signals.append(_make_reinforcement(obs))
        # 下一轮是补充或扩展 → 当前轮也被接受（用户是在此基础上追加）
        elif set(next_obs.indicators_retrieved) > set(obs.indicators_retrieved):
            signals.append(_make_reinforcement(obs))

    # 最后一轮：如果 session 正常结束（无 error），也标记为接受
    last = session_observations[-1]
    if last.error is None:
        signals.append(_make_reinforcement(last))

    return signals


def _make_reinforcement(obs: Observation) -> DetectedSignal:
    return DetectedSignal(
        type=SignalType.REINFORCEMENT,
        session_id="",
        turn_pair=(obs.turn, obs.turn),
        industry=obs.industry,
        scenario=obs.scenarios_retrieved[0] if obs.scenarios_retrieved else "",
        indicators_before=obs.indicators_retrieved,
        indicators_after=obs.indicators_retrieved,
        template_before=obs.template_matched,
        template_after=obs.template_matched,
        query_before=obs.query,
        query_after="",
        user_anon_id=obs.user_anon_id,
    )
