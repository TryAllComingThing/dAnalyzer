"""语义邻近传播 + 跨行业迁移

行业内：纠正发生时，邻近指标也获得小幅权重调整。
跨行业：通过种子映射传播到其他行业。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from learn.ingest.models import Hypothesis, HypothesisType, PropagationEntry


def propagate_correction(
    hypothesis: Hypothesis,
    proximity_matrix: dict[str, dict[str, float]],
    max_neighbors: int = 5,
    proximity_threshold: float = 0.6,
    propagation_factor: float = 0.25,
) -> list[PropagationEntry]:
    """行业内语义传播

    对 hypothesis 中涉及的每条指标变更，查找其邻近指标，
    产生小幅同方向传播。

    Args:
        hypothesis: 包含 operations 的假设
        proximity_matrix: 指标共现矩阵
        max_neighbors: 每个源指标最多传播到几个邻居
        proximity_threshold: 邻近度阈值
        propagation_factor: 传播幅度系数（相对源 delta）
    """
    source_indicators = _extract_affected_indicators(hypothesis)
    if not source_indicators:
        return []

    entries: list[PropagationEntry] = []
    seen: set[str] = set(source_indicators)

    for indicator in source_indicators:
        delta = _delta_for_indicator(hypothesis, indicator)
        if delta == 0:
            continue

        neighbors = proximity_matrix.get(indicator, {})
        candidates = [
            (n, p)
            for n, p in neighbors.items()
            if p >= proximity_threshold and n not in seen
        ]
        candidates.sort(key=lambda x: x[1], reverse=True)

        for neighbor, proximity in candidates[:max_neighbors]:
            propagated_delta = round(delta * propagation_factor * proximity, 4)
            entries.append(
                PropagationEntry(
                    indicator=neighbor,
                    delta=propagated_delta,
                    reason="semantic_propagation",
                    mapping_confidence=round(proximity, 4),
                )
            )
            seen.add(neighbor)

    return entries


def cross_industry_propagate(
    hypothesis: Hypothesis,
    cross_industry_mappings: dict,
    knowledge_dir: str | None = None,
    transfer_weight_factor: float = 0.25,
) -> list[PropagationEntry]:
    """跨行业迁移传播

    查询 cross_industry_mappings.yaml 中的映射，
    在目标行业产生小幅权重调整。

    跨行业迁移永远走 progressive_apply，幅度远小于行业内调整。
    """
    source_industry = hypothesis.industry
    source_indicators = _extract_affected_indicators(hypothesis)
    if not source_indicators:
        return []

    mappings_list = cross_industry_mappings.get("mappings", {})
    entries: list[PropagationEntry] = []

    for mapping_key, pairs in mappings_list.items():
        # 检查 mapping 是否匹配源行业
        if not mapping_key.startswith(f"{source_industry}_to_"):
            continue
        target_industry = mapping_key[len(source_industry) + 4:]  # "fmcg_to_" → ""

        for pair in pairs:
            if pair.get("from") not in source_indicators:
                continue

            source_delta = _delta_for_indicator(hypothesis, pair["from"])
            mapping_conf = pair.get("confidence", 0.5)

            # 迁移幅度 = 源幅度 × transfer_weight_factor × mapping_confidence
            transfer_delta = round(
                source_delta * transfer_weight_factor * mapping_conf, 4
            )
            entries.append(
                PropagationEntry(
                    indicator=pair["to"],
                    delta=transfer_delta,
                    reason="cross_industry_transfer",
                    mapping_confidence=mapping_conf,
                )
            )

    return entries


def load_cross_industry_mappings(
    mapping_file: str | Path,
) -> dict:
    """加载跨行业映射文件"""
    path = Path(mapping_file)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _extract_affected_indicators(hypothesis: Hypothesis) -> set[str]:
    """从 hypothesis 中提取受影响的指标"""
    indicators: set[str] = set()
    current = hypothesis.current or {}
    suggested = hypothesis.suggested or {}

    for key in set(list(current.keys()) + list(suggested.keys())):
        if key not in ("layer", "file", "path", "field", "dimension", "type"):
            indicators.add(key)

    if hypothesis.evidence and hypothesis.evidence.signal_type:
        pass

    return indicators


def _delta_for_indicator(hypothesis: Hypothesis, indicator: str) -> float:
    """计算 hypothesis 中某个指标的变更幅度

    正 = 提权/新增，负 = 降权/移除
    """
    suggested = hypothesis.suggested or {}
    current = hypothesis.current or {}

    if indicator in suggested and indicator not in current:
        return 1.0  # 新增
    if indicator not in suggested and indicator in current:
        return -1.0  # 移除

    suggested_val = suggested.get(indicator)
    current_val = current.get(indicator)

    if isinstance(suggested_val, (int, float)) and isinstance(current_val, (int, float)):
        return suggested_val - current_val

    return 0.0
