"""补丁栈构建器

从 _canonical/ + _patches/ → 重建 _active/ 目录。
管理补丁的合并、冲突检测和废弃。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from learn.ingest.models import HypothesisStatus, Patch


def rebuild_active(
    canonical_dir: str | Path,
    patches_dir: str | Path,
    active_dir: str | Path,
) -> dict[str, int]:
    """重建 _active/ 目录

    1. 加载 _canonical/ 下所有基线文件
    2. 加载 _patches/ 下所有状态非 defunct 的补丁
    3. 按创建时间排序，依次 apply
    4. 同一字段的多个 patch delta 取平均（冲突合并）
    5. 输出到 _active/

    Returns:
        {file_path: patches_applied}
    """
    canonical_dir = Path(canonical_dir)
    patches_dir = Path(patches_dir)
    active_dir = Path(active_dir)
    active_dir.mkdir(parents=True, exist_ok=True)

    # 加载 canonical
    canonical_files = _load_canonical_files(canonical_dir)

    # 加载并排序 active patches
    patches = _load_sorted_patches(patches_dir)
    if not patches:
        _write_active_files(active_dir, canonical_files)
        return {}

    # 按文件分组 patches
    patches_by_file: dict[str, list[Patch]] = {}
    for p in patches:
        key = p.target.path
        patches_by_file.setdefault(key, []).append(p)

    # 合并 patches 到 canonical
    active_files = dict(canonical_files)
    stats: dict[str, int] = {}

    for file_path, file_patches in patches_by_file.items():
        base = canonical_files.get(file_path, {})
        merged, count = _merge_into(base, file_patches)
        active_files[file_path] = merged
        stats[file_path] = count

    # 写入 _active/
    _write_active_files(active_dir, active_files)

    return stats


def get_active_patches(patches_dir: str | Path) -> list[dict]:
    """获取所有 active 状态的补丁摘要"""
    patches_dir = Path(patches_dir)
    if not patches_dir.is_dir():
        return []

    result: list[dict] = []
    for pf in sorted(patches_dir.glob("*.yaml")):
        patch = _load_patch_file(pf)
        if patch and patch.status != HypothesisStatus.DEFUNCT:
            result.append({
                "id": patch.id,
                "type": patch.type.value,
                "status": patch.status.value,
                "target": patch.target.path,
                "validated_confidence": patch.validated_confidence,
                "operations": len(patch.operations),
                "created": patch.created,
            })
    return result


def defunct_patch(patch_id: str, patches_dir: str | Path) -> bool:
    """标记补丁为 defunct（不删除，保留审计追踪）

    Returns:
        True 如果成功标记
    """
    patches_dir = Path(patches_dir)
    patch_path = patches_dir / f"{patch_id}.yaml"
    if not patch_path.exists():
        return False

    patch = _load_patch_file(patch_path)
    if patch is None:
        return False

    # 写入 defunct 状态的 patch
    import copy
    updated = copy.deepcopy(patch)
    import dataclasses
    updated = dataclasses.replace(updated, status=HypothesisStatus.DEFUNCT)

    # Write back
    data = _patch_to_dict(updated)
    with open(patch_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    return True


# ============================================================
# 内部辅助
# ============================================================


def _load_canonical_files(canonical_dir: Path) -> dict[str, dict]:
    """加载 canonical 目录下所有 YAML 文件"""
    if not canonical_dir.is_dir():
        return {}
    files: dict[str, dict] = {}
    for f in canonical_dir.rglob("*.yaml"):
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
            rel = str(f.relative_to(canonical_dir))
            files[rel] = data
    return files


def _load_sorted_patches(patches_dir: Path) -> list[Patch]:
    """加载非 defunct 补丁，按创建时间排序"""
    if not patches_dir.is_dir():
        return []

    patches: list[Patch] = []
    for pf in patches_dir.glob("*.yaml"):
        patch = _load_patch_file(pf)
        if patch and patch.status != HypothesisStatus.DEFUNCT:
            patches.append(patch)

    patches.sort(key=lambda p: p.created)
    return patches


def _load_patch_file(path: Path) -> Patch | None:
    """从 YAML 文件加载单个 Patch"""
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return None

    from learn.ingest.models import (
        Evidence,
        HypothesisTarget,
        HypothesisType,
        PatchOp,
        PatchOperation,
        PropagationEntry,
    )

    ops = [
        PatchOperation(
            op=PatchOp(o.get("op", "adjust_weight")),
            target=o.get("target", ""),
            delta=o.get("delta", 0.0),
            current_weight=o.get("current_weight", 0.0),
            reason=o.get("reason", ""),
        )
        for o in data.get("operations", [])
    ]
    props = [
        PropagationEntry(
            indicator=p.get("indicator", ""),
            delta=p.get("delta", 0.0),
            reason=p.get("reason", ""),
            mapping_confidence=p.get("mapping_confidence", 1.0),
        )
        for p in data.get("propagation", [])
    ]
    target_data = data.get("target", {})
    target = HypothesisTarget(
        layer=target_data.get("layer", "canonical"),
        file=target_data.get("file", ""),
        path=target_data.get("path", ""),
        field=target_data.get("field"),
    )
    evidence = None
    if data.get("evidence"):
        ev = data["evidence"]
        evidence = Evidence(
            signal_type=ev.get("signal_type", "correction"),
            signal_ids=ev.get("signal_ids", []),
            frequency=ev.get("frequency", 0),
            period_days=ev.get("period_days", 1),
            unique_sessions=ev.get("unique_sessions", 0),
        )

    return Patch(
        id=data.get("id", ""),
        status=HypothesisStatus(data.get("status", "progressive")),
        type=HypothesisType(data.get("type", "keyword_adjustment")),
        created=data.get("created", ""),
        last_updated=data.get("last_updated", ""),
        target=target,
        operations=ops,
        propagation=props,
        evidence=evidence,
        validated_confidence=data.get("validated_confidence", 0.0),
        schema_version=data.get("schema_version", 2),
    )


def _merge_into(base: dict, patches: list[Patch]) -> tuple[dict, int]:
    """合并多个 patches 到 base dict，返回 (merged, patches_applied)"""
    import copy
    result = copy.deepcopy(base)
    field_deltas: dict[str, list[float]] = {}

    for patch in patches:
        for op in patch.operations:
            key = op.target
            field_deltas.setdefault(key, []).append(op.delta)

    for key, deltas in field_deltas.items():
        avg = sum(deltas) / len(deltas)
        _apply_deep_delta(result, key, avg)

    return result, len(patches)


def _apply_deep_delta(data: dict, key: str, delta: float) -> None:
    """在嵌套 dict 中查找并应用 delta"""
    if key in data and isinstance(data[key], (int, float)):
        data[key] = round(data[key] + delta, 4)
        return
    for v in data.values():
        if isinstance(v, dict):
            _apply_deep_delta(v, key, delta)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    _apply_deep_delta(item, key, delta)


def _write_active_files(active_dir: Path, files: dict[str, dict]) -> None:
    """写入合并后的文件到 _active/"""
    for rel_path, data in files.items():
        full_path = active_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def _patch_to_dict(patch: Patch) -> dict:
    """Patch → 可序列化 dict"""
    return {
        "id": patch.id,
        "status": patch.status.value,
        "type": patch.type.value,
        "created": patch.created,
        "last_updated": patch.last_updated,
        "target": {
            "layer": patch.target.layer,
            "file": patch.target.file,
            "path": patch.target.path,
            "field": patch.target.field,
        },
        "operations": [
            {
                "op": o.op.value,
                "target": o.target,
                "delta": o.delta,
                "current_weight": o.current_weight,
                "reason": o.reason,
            }
            for o in patch.operations
        ],
        "propagation": [
            {
                "indicator": p.indicator,
                "delta": p.delta,
                "reason": p.reason,
                "mapping_confidence": p.mapping_confidence,
            }
            for p in patch.propagation
        ],
        "validated_confidence": patch.validated_confidence,
        "schema_version": patch.schema_version,
    }
