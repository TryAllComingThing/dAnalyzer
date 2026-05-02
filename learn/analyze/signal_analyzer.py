"""信号聚类 → 假设生成

从 JSONL 信号中聚类，产出结构化 hypothesis。
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime, timezone

from learn.ingest.models import (
    DetectedSignal,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    HypothesisTarget,
    HypothesisType,
    SignalCluster,
    SignalType,
)

# 聚类最少出现次数
MIN_FREQ: dict[SignalType, int] = {
    SignalType.CORRECTION: 3,
    SignalType.SUPPLEMENT: 3,
    SignalType.REFINEMENT: 3,
    SignalType.EXTENSION: 5,
    SignalType.L3_FALLBACK: 3,
}

ClusterKey = tuple[str, str, str]  # (industry, scenario, direction_key)


# ============================================================
# 聚类
# ============================================================


def cluster_corrections(signals: list[DetectedSignal]) -> list[SignalCluster]:
    """按 industry + scenario + 方向 (before → after) 分组"""
    sigs = [s for s in signals if s.type == SignalType.CORRECTION]
    groups: dict[ClusterKey, list[DetectedSignal]] = defaultdict(list)
    for s in sigs:
        key = (s.industry, s.scenario, _correction_direction(s))
        groups[key].append(s)
    return _build_clusters(SignalType.CORRECTION, groups)


def cluster_supplements(signals: list[DetectedSignal]) -> list[SignalCluster]:
    """按 industry + scenario + 被追加的 indicator 分组"""
    sigs = [s for s in signals if s.type == SignalType.SUPPLEMENT]
    groups: dict[ClusterKey, list[DetectedSignal]] = defaultdict(list)
    for s in sigs:
        for ind in s.added_indicators:
            key = (s.industry, s.scenario, f"add:{ind}")
            groups[key].append(s)
    return _build_clusters(SignalType.SUPPLEMENT, groups)


def cluster_refinements(signals: list[DetectedSignal]) -> list[SignalCluster]:
    """按 industry + scenario + 调整方向分组"""
    sigs = [s for s in signals if s.type == SignalType.REFINEMENT]
    groups: dict[ClusterKey, list[DetectedSignal]] = defaultdict(list)
    for s in sigs:
        key = (s.industry, s.scenario, _refinement_direction(s))
        groups[key].append(s)
    return _build_clusters(SignalType.REFINEMENT, groups)


def cluster_extensions(signals: list[DetectedSignal]) -> list[SignalCluster]:
    """按 skill_chain 前缀相似度分组

    使用 skill_chain 的 LCS 前缀作为分组键。
    """
    sigs = [s for s in signals if s.type == SignalType.EXTENSION]
    if not sigs:
        return []

    # 使用 after indicators 作为 skill_chain 代理（extension signals 中
    # indicators_after 存储了扩展后的 skill_chain 的文本表示）
    groups: dict[ClusterKey, list[DetectedSignal]] = defaultdict(list)
    for s in sigs:
        prefix = _skill_chain_prefix(s)
        key = (s.industry, s.scenario, prefix)
        groups[key].append(s)
    return _build_clusters(SignalType.EXTENSION, groups)


def cluster_l3_fallbacks(signals: list[DetectedSignal]) -> list[SignalCluster]:
    """按 N-gram 关键词提取分组

    从 query_before 中提取 2-gram 作为知识盲区关键词。
    """
    sigs = [s for s in signals if s.type == SignalType.L3_FALLBACK]
    groups: dict[ClusterKey, list[DetectedSignal]] = defaultdict(list)
    for s in sigs:
        keywords = _extract_bigrams(s.query_before)
        for kw in keywords:
            key = (s.industry, s.scenario, f"l3:{kw}")
            groups[key].append(s)
    return _build_clusters(SignalType.L3_FALLBACK, groups)


def cluster_preferences(signals: list[DetectedSignal]) -> list[SignalCluster]:
    """按 industry + scenario + preference 类型分组"""
    sigs = [
        s
        for s in signals
        if s.type in (SignalType.PREFERENCE_CHART, SignalType.PREFERENCE_REPORT)
    ]
    groups: dict[ClusterKey, list[DetectedSignal]] = defaultdict(list)
    for s in sigs:
        direction = s.indicators_after[0] if s.indicators_after else "unknown"
        key = (s.industry, s.scenario, f"{s.type.value}:{direction}")
        groups[key].append(s)
    return _build_clusters(SignalType.PREFERENCE_CHART, groups)


# ============================================================
# 假设生成
# ============================================================


def generate_hypotheses(clusters: list[SignalCluster]) -> list[Hypothesis]:
    """从聚类结果生成假设"""
    hypotheses: list[Hypothesis] = []
    for cluster in clusters:
        if cluster.frequency < MIN_FREQ.get(cluster.signal_type, 3):
            continue

        h_type = _infer_hypothesis_type(cluster)
        target = _infer_target(cluster, h_type)
        hypothesis = Hypothesis(
            id=_make_hypothesis_id(cluster),
            type=h_type,
            industry=cluster.industry,
            evidence=Evidence(
                signal_type=cluster.signal_type,
                signal_ids=cluster.signal_ids,
                frequency=cluster.frequency,
                period_days=_period_days(cluster.signal_ids),
                unique_sessions=cluster.unique_sessions,
                user_diversity_ratio=cluster.unique_sessions / max(cluster.frequency, 1),
            ),
            target=target,
            confidence=0.0,  # 由 validate 阶段计算
            status=HypothesisStatus.PENDING_VALIDATION,
            current=cluster.details.get("current"),
            suggested=cluster.details.get("suggested"),
            dimension=cluster.details.get("dimension", ""),
        )
        hypotheses.append(hypothesis)
    return hypotheses


# ============================================================
# 内部辅助
# ============================================================


def _build_clusters(
    stype: SignalType, groups: dict[ClusterKey, list[DetectedSignal]]
) -> list[SignalCluster]:
    clusters: list[SignalCluster] = []
    for (industry, scenario, direction), sigs in groups.items():
        signal_ids = [f"{s.session_id}:{s.turn_pair[0]}:{s.turn_pair[1]}" for s in sigs]
        sessions = {s.session_id for s in sigs}
        users = {s.user_anon_id for s in sigs if s.user_anon_id}
        clusters.append(
            SignalCluster(
                signal_type=stype,
                industry=industry,
                scenario=scenario,
                signal_ids=signal_ids,
                frequency=len(sigs),
                unique_sessions=len(sessions),
                direction_count=1,
                user_anon_ids=sorted(users),
                details={
                    "direction": direction,
                    "indicators_before": sigs[0].indicators_before,
                    "indicators_after": sigs[0].indicators_after,
                },
            )
        )
    return clusters


def _correction_direction(signal: DetectedSignal) -> str:
    before = ",".join(sorted(signal.indicators_before))
    after = ",".join(sorted(signal.indicators_after))
    return f"{before}->{after}"


def _refinement_direction(signal: DetectedSignal) -> str:
    removed = ",".join(sorted(signal.replaced_indicators))
    added = ",".join(sorted(signal.added_indicators))
    return f"-{removed}+{added}"


def _skill_chain_prefix(signal: DetectedSignal) -> str:
    after = signal.indicators_after if signal.indicators_after else []
    return ",".join(after[:3]) if after else "unknown"


def _extract_bigrams(text: str) -> list[str]:
    if not text:
        return []
    # 简单字符 bigram（中文场景）
    chars = re.sub(r"\s+", "", text)
    if len(chars) < 2:
        return [chars] if chars else []
    bigrams: list[str] = []
    for i in range(len(chars) - 1):
        bg = chars[i : i + 2]
        if bg not in bigrams:
            bigrams.append(bg)
    return bigrams[:5]  # 最多取前 5 个


def _infer_hypothesis_type(cluster: SignalCluster) -> HypothesisType:
    mapping = {
        SignalType.CORRECTION: HypothesisType.KEYWORD_ADJUSTMENT,
        SignalType.SUPPLEMENT: HypothesisType.INDICATOR_COMBINATION,
        SignalType.REFINEMENT: HypothesisType.INDICATOR_WEIGHT,
        SignalType.EXTENSION: HypothesisType.TEMPLATE_ROUTING,
        SignalType.L3_FALLBACK: HypothesisType.INTENT_NEW,
        SignalType.PREFERENCE_CHART: HypothesisType.PREFERENCE_CHART,
        SignalType.PREFERENCE_REPORT: HypothesisType.PREFERENCE_REPORT,
    }
    return mapping.get(cluster.signal_type, HypothesisType.INDICATOR_WEIGHT)


def _infer_target(
    cluster: SignalCluster, h_type: HypothesisType
) -> HypothesisTarget:
    if h_type in (HypothesisType.KEYWORD_ADJUSTMENT, HypothesisType.INDICATOR_WEIGHT):
        return HypothesisTarget(
            layer="canonical",
            file=f"{cluster.scenario}.yaml",
            path=f"knowledge/industry/{cluster.industry}/scenarios/{cluster.scenario}.yaml",
            field="content.required",
        )
    elif h_type == HypothesisType.INDICATOR_COMBINATION:
        return HypothesisTarget(
            layer="canonical",
            file=f"{cluster.scenario}.yaml",
            path=f"knowledge/industry/{cluster.industry}/scenarios/{cluster.scenario}.yaml",
            field="content.optional",
        )
    elif h_type == HypothesisType.TEMPLATE_ROUTING:
        return HypothesisTarget(
            layer="routing",
            file="intent-routing.yaml",
            path="knowledge/intent-routing.yaml",
            field="weights",
        )
    elif h_type == HypothesisType.PREFERENCE_CHART:
        return HypothesisTarget(
            layer="industry",
            file="preferences.yaml",
            path=f"knowledge/industry/{cluster.industry}/preferences.yaml",
            field="chart_defaults",
        )
    elif h_type == HypothesisType.PREFERENCE_REPORT:
        return HypothesisTarget(
            layer="industry",
            file="preferences.yaml",
            path=f"knowledge/industry/{cluster.industry}/preferences.yaml",
            field="report_defaults",
        )
    else:
        return HypothesisTarget(
            layer="canonical",
            file=f"{cluster.scenario}.yaml",
            path=f"knowledge/industry/{cluster.industry}/scenarios/{cluster.scenario}.yaml",
        )


def _make_hypothesis_id(cluster: SignalCluster) -> str:
    raw = f"{cluster.signal_type.value}:{cluster.industry}:{cluster.scenario}:{cluster.details.get('direction','')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _period_days(signal_ids: list[str]) -> int:
    """根据 signal_ids 估算时间跨度（简化：用数量近似）"""
    return max(len(signal_ids), 1)
