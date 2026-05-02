"""共现矩阵构建

扫描 scenario 配置，构建指标共现矩阵，归一化为邻近度 [0, 1]。
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml


def build_cooccurrence_matrix(
    knowledge_dir: str | Path, industry: str | None = None
) -> dict[str, dict[str, float]]:
    """构建指标共现矩阵

    扫描 knowledge/industry/{industry}/scenarios/*.yaml，
    统计指标在同一 scenario 的 required + optional 列表中的共现频次。

    Args:
        knowledge_dir: knowledge/ 目录路径
        industry: 限定行业，None 表示跨所有行业

    Returns:
        嵌套 dict: indicator_i -> {indicator_j: proximity (0-1)}
    """
    knowledge_dir = Path(knowledge_dir)
    cooccur: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    industries = [industry] if industry else _discover_industries(knowledge_dir)

    for ind in industries:
        scenario_dir = knowledge_dir / "industry" / ind / "scenarios"
        if not scenario_dir.is_dir():
            continue
        for sfile in scenario_dir.glob("*.yaml"):
            try:
                indicators = _extract_indicators(sfile)
            except Exception:
                continue
            for i in indicators:
                for j in indicators:
                    if i != j:
                        cooccur[i][j] += 1

    if not cooccur:
        return {}

    # 归一化到 [0, 1]
    max_count = max(max(neighbors.values()) for neighbors in cooccur.values())
    if max_count == 0:
        return {}

    matrix: dict[str, dict[str, float]] = {}
    for i, neighbors in cooccur.items():
        matrix[i] = {j: round(count / max_count, 4) for j, count in neighbors.items()}
    return matrix


def get_neighbors(
    matrix: dict[str, dict[str, float]],
    indicator: str,
    threshold: float = 0.6,
    max_neighbors: int = 5,
) -> list[tuple[str, float]]:
    """获取指定指标的邻近指标列表

    Returns:
        [(indicator_id, proximity), ...] 按邻近度降序
    """
    neighbors = matrix.get(indicator, {})
    candidates = [
        (n, p) for n, p in neighbors.items() if p >= threshold
    ]
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:max_neighbors]


def _extract_indicators(scenario_file: Path) -> list[str]:
    """从 scenario YAML 中提取 required + optional indicators"""
    with open(scenario_file, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    content = data.get("content", {})
    required = content.get("required", []) or []
    optional = content.get("optional", []) or []
    return required + optional


def _discover_industries(knowledge_dir: Path) -> list[str]:
    """发现 knowledge/industry/ 下的所有行业目录"""
    industry_dir = knowledge_dir / "industry"
    if not industry_dir.is_dir():
        return []
    return [
        d.name
        for d in industry_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")
    ]
