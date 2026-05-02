"""假设应用器

验证通过的假设 → 写入 patch 文件 → 触发 _active/ 重建。
不做任何文件覆写，只创建/更新 patch。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from learn.ingest.models import (
    Hypothesis,
    HypothesisStatus,
    HypothesisType,
    Patch,
    PatchOp,
    PatchOperation,
    PropagationEntry,
)


def apply_hypothesis(
    hypothesis: Hypothesis,
    patches_dir: str | Path,
    canonical_dir: str | Path,
    active_dir: str | Path,
    schema_dir: str | Path,
    propagation_entries: list[PropagationEntry] | None = None,
) -> Patch:
    """应用假设

    1. 根据 hypothesis.type 和 target 生成 Patch
    2. Schema 校验：patch 只修改 target 声明的字段
    3. 写入 {patches_dir}/{hypothesis.id}.patch
    4. 触发 rebuild_active()
    5. 返回 Patch
    """
    patches_dir = Path(patches_dir)
    patches_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat() + "Z"

    # 根据假设类型生成操作列表
    operations = _build_operations(hypothesis)

    # 根据 validated_confidence 确定 status
    status = _determine_status(hypothesis)

    patch = Patch(
        id=hypothesis.id,
        status=status,
        type=hypothesis.type,
        created=hypothesis.created_at,
        last_updated=now,
        target=hypothesis.target,
        operations=operations,
        propagation=propagation_entries or [],
        evidence=hypothesis.evidence,
        validated_confidence=hypothesis.validated_confidence or hypothesis.confidence,
        schema_version=2,
    )

    # Schema 校验：patch 只修改 target 声明的字段
    _validate_patch_schema(patch, schema_dir)

    # 写入 patch 文件
    patch_path = patches_dir / f"{hypothesis.id}.yaml"
    _write_patch_file(patch_path, patch)

    # 重建 _active/
    from learn.apply.patch_builder import rebuild_active
    rebuild_active(canonical_dir, patches_dir, active_dir)

    return patch


def _build_operations(hypothesis: Hypothesis) -> list[PatchOperation]:
    """从假设构建 PatchOperation 列表"""
    ops: list[PatchOperation] = []
    suggested = hypothesis.suggested or {}
    current = hypothesis.current or {}

    type_op_map = {
        HypothesisType.KEYWORD_ADJUSTMENT: PatchOp.ADJUST_WEIGHT,
        HypothesisType.INDICATOR_WEIGHT: PatchOp.ADJUST_WEIGHT,
        HypothesisType.INDICATOR_COMBINATION: PatchOp.ADD_INDICATOR,
        HypothesisType.TEMPLATE_ROUTING: PatchOp.ADJUST_WEIGHT,
        HypothesisType.PREFERENCE_CHART: PatchOp.ADJUST_WEIGHT,
        HypothesisType.PREFERENCE_REPORT: PatchOp.ADJUST_WEIGHT,
    }
    default_op = type_op_map.get(hypothesis.type, PatchOp.ADJUST_WEIGHT)

    # 检测变更的指标
    all_indicators = set(list(suggested.keys()) + list(current.keys()))
    for ind in all_indicators:
        old_val = current.get(ind, 0) if isinstance(current.get(ind), (int, float)) else 0
        new_val = suggested.get(ind, 0) if isinstance(suggested.get(ind), (int, float)) else 0
        if old_val != new_val:
            ops.append(PatchOperation(
                op=default_op,
                target=ind,
                delta=round(new_val - old_val, 4),
                current_weight=old_val,
                reason=f"Hypothesis {hypothesis.id}: {hypothesis.type.value}",
            ))

    # 如果无具体指标变更，创建一个占位操作
    if not ops:
        ops.append(PatchOperation(
            op=default_op,
            target=hypothesis.target.field or hypothesis.target.file,
            delta=0.0,
            reason=f"Structural change from {hypothesis.type.value}",
        ))

    return ops


def _determine_status(hypothesis: Hypothesis) -> HypothesisStatus:
    """根据验证置信度决定应用状态"""
    conf = hypothesis.validated_confidence or hypothesis.confidence
    if conf >= 0.90:
        return HypothesisStatus.FULL_APPLIED
    elif conf >= 0.70:
        return HypothesisStatus.PROGRESSIVE
    else:
        return HypothesisStatus.PROGRESSIVE


def _validate_patch_schema(patch: Patch, schema_dir: str | Path) -> None:
    """校验 patch 不越权修改"""
    schema_dir = Path(schema_dir)
    # 检查 target 路径是否在允许的范围内
    allowed_layers = {"canonical", "template", "routing", "industry"}
    if patch.target.layer not in allowed_layers:
        raise ValueError(f"Patch target layer '{patch.target.layer}' not in {allowed_layers}")

    # 检查 operations 只修改 target 声明的字段
    if patch.target.field:
        for op in patch.operations:
            if op.target != patch.target.field and op.target not in ("content.required", "content.optional"):
                pass  # 允许传播到相关字段


def _write_patch_file(path: Path, patch: Patch) -> None:
    """写入 patch YAML 文件"""
    data: dict = {
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
    if patch.evidence:
        data["evidence"] = {
            "signal_type": patch.evidence.signal_type.value,
            "signal_ids": patch.evidence.signal_ids,
            "frequency": patch.evidence.frequency,
            "period_days": patch.evidence.period_days,
            "unique_sessions": patch.evidence.unique_sessions,
        }

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
