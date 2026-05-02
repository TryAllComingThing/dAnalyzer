"""反事实信号检测器

当用户纠正后的指标恰好出现在检索候选项中（但不在返回结果中）时，
这表示系统"知道"正确答案但没把它排到前面——排序问题而非知识缺失。
"""

from __future__ import annotations

from learn.ingest.models import Candidate, CounterfactualResult, Observation


def check_counterfactual(
    observation: Observation,
    user_selected_indicators: list[str],
) -> CounterfactualResult | None:
    """检查用户选择的指标是否在 candidates 中但不在 retrieved 中。

    Args:
        observation: 当前轮 observation（含 candidates 列表）
        user_selected_indicators: 用户本轮实际选择的指标

    Returns:
        CounterfactualResult 如果存在候选命中，否则 None
    """
    if not observation.indicators_candidates or not user_selected_indicators:
        return None

    retrieved = set(observation.indicators_retrieved)
    user_selected = set(user_selected_indicators)

    # 用户选中的指标中，哪些在 candidates 中但不在 retrieved 中
    hit_indicators: list[str] = []
    hit_ranks: list[int] = []

    for cand in observation.indicators_candidates:
        if cand.id in user_selected and cand.id not in retrieved:
            hit_indicators.append(cand.id)
            hit_ranks.append(cand.rank)

    if hit_indicators:
        return CounterfactualResult(
            candidate_hit=True,
            hit_indicators=hit_indicators,
            hit_ranks=hit_ranks,
            user_selected=sorted(user_selected),
            indicators_retrieved=sorted(retrieved),
        )

    return None
