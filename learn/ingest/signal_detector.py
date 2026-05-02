"""纠正/补充/调整/扩展信号检测器

纯函数模块。对同一 session 内相邻的两条 observation 做结构化对比，
产出 correction / supplement / refinement / extension 信号。
"""

from __future__ import annotations

import re
from typing import Final

from learn.ingest.models import DetectionMethod, DetectedSignal, Observation, SignalType

# 否定/纠正常见模式（中文 + 英文）
CORRECTION_PATTERNS: Final[list[str]] = [
    r"(?:不是|不对|错了|我要的是|应该是|改成|换成|纠正|修正|重新)",
    r"(?:not|could be wrong|should be|actually|I meant|change to|replace)",
]

# 替换比例阈值：新增指标占总数的比例 >= 此值 + 否定词 = correction
CORRECTION_REPLACEMENT_RATIO: Final[float] = 0.5


def _has_correction_signal(query: str) -> bool:
    """检测 query 文本是否包含纠正意图"""
    for pattern in CORRECTION_PATTERNS:
        if re.search(pattern, query):
            return True
    return False


def classify_query_pair(
    prev: Observation, curr: Observation
) -> DetectedSignal | None:
    """对同一 session 内相邻的两条 observation 分类。

    返回 DetectedSignal 或 None（unrelated / insufficient_data / no_change / narrowing 不产生信号）。
    """
    # 场景变了 → 换话题，不产生信号
    if set(prev.scenarios_retrieved) != set(curr.scenarios_retrieved):
        return None

    prev_inds = set(prev.indicators_retrieved)
    curr_inds = set(curr.indicators_retrieved)

    # 都不为空才做对比
    if not prev_inds or not curr_inds:
        return None

    # 完全不相交 → 纠正
    if prev_inds.isdisjoint(curr_inds):
        return DetectedSignal(
            type=SignalType.CORRECTION,
            session_id="",
            turn_pair=(prev.turn, curr.turn),
            industry=prev.industry,
            scenario=prev.scenarios_retrieved[0],
            indicators_before=sorted(prev_inds),
            indicators_after=sorted(curr_inds),
            template_before=prev.template_matched,
            template_after=curr.template_matched,
            query_before=prev.query,
            query_after=curr.query,
            detection_method=DetectionMethod.DISJOINT,
            replacement_ratio=1.0,
            replaced_indicators=sorted(prev_inds),
            added_indicators=sorted(curr_inds),
            kept_indicators=[],
            user_anon_id=curr.user_anon_id,
        )

    # 纯扩充 → 补充
    if curr_inds > prev_inds:
        return DetectedSignal(
            type=SignalType.SUPPLEMENT,
            session_id="",
            turn_pair=(prev.turn, curr.turn),
            industry=prev.industry,
            scenario=prev.scenarios_retrieved[0],
            indicators_before=sorted(prev_inds),
            indicators_after=sorted(curr_inds),
            template_before=prev.template_matched,
            template_after=curr.template_matched,
            query_before=prev.query,
            query_after=curr.query,
            detection_method=DetectionMethod.PURE_ADDITION,
            added_indicators=sorted(curr_inds - prev_inds),
            kept_indicators=sorted(prev_inds & curr_inds),
            user_anon_id=curr.user_anon_id,
        )

    # 纯缩减 → 用户自己缩小范围，不记录
    if curr_inds < prev_inds:
        return None

    # 完全一致 → 静默重查，不记录
    if prev_inds == curr_inds:
        return None

    # 部分重叠 → 检查是否为部分纠正
    replaced = prev_inds - curr_inds
    added = curr_inds - prev_inds
    kept = prev_inds & curr_inds
    replacement_ratio = len(added) / len(curr_inds)

    if replacement_ratio >= CORRECTION_REPLACEMENT_RATIO and _has_correction_signal(curr.query):
        return DetectedSignal(
            type=SignalType.CORRECTION,
            session_id="",
            turn_pair=(prev.turn, curr.turn),
            industry=prev.industry,
            scenario=prev.scenarios_retrieved[0],
            indicators_before=sorted(prev_inds),
            indicators_after=sorted(curr_inds),
            template_before=prev.template_matched,
            template_after=curr.template_matched,
            query_before=prev.query,
            query_after=curr.query,
            detection_method=DetectionMethod.PARTIAL_REPLACEMENT,
            replacement_ratio=round(replacement_ratio, 2),
            replaced_indicators=sorted(replaced),
            added_indicators=sorted(added),
            kept_indicators=sorted(kept),
            user_anon_id=curr.user_anon_id,
        )

    # 否则 → 调整
    return DetectedSignal(
        type=SignalType.REFINEMENT,
        session_id="",
        turn_pair=(prev.turn, curr.turn),
        industry=prev.industry,
        scenario=prev.scenarios_retrieved[0],
        indicators_before=sorted(prev_inds),
        indicators_after=sorted(curr_inds),
        query_before=prev.query,
        query_after=curr.query,
        detection_method=DetectionMethod.STRUCTURED_COMPARISON,
        replaced_indicators=sorted(replaced),
        added_indicators=sorted(added),
        kept_indicators=sorted(kept),
        user_anon_id=curr.user_anon_id,
    )


def detect_extension(
    prev: Observation, curr: Observation
) -> DetectedSignal | None:
    """检测扩展信号：scenario 不变但 skill_chain 不同。

    在当前 implementation 中，extension 检测需要 session 级上下文
    （同一 scenario 下的累积 skill_chain），此处提供单对检测接口。
    """
    if set(prev.scenarios_retrieved) != set(curr.scenarios_retrieved):
        return None
    if prev.skill_chain_actual == curr.skill_chain_actual:
        return None
    if not prev.skill_chain_actual or not curr.skill_chain_actual:
        return None

    prev_steps = set(prev.skill_chain_actual)
    curr_steps = set(curr.skill_chain_actual)

    # 当前步骤包含前一步骤 + 新步骤 → extension
    if curr_steps > prev_steps:
        return DetectedSignal(
            type=SignalType.EXTENSION,
            session_id="",
            turn_pair=(prev.turn, curr.turn),
            industry=prev.industry,
            scenario=prev.scenarios_retrieved[0],
            indicators_before=prev.indicators_retrieved,
            indicators_after=curr.indicators_retrieved,
            query_before=prev.query,
            query_after=curr.query,
            detection_method=DetectionMethod.STRUCTURED_COMPARISON,
            user_anon_id=curr.user_anon_id,
        )
    return None
