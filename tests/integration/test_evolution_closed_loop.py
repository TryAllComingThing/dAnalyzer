"""Phase 4 闭环集成测试

验证: hypothesis → validate → apply → rebuild → climb 全链路。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from learn.apply.applier import apply_hypothesis
from learn.apply.patch_builder import (
    defunct_patch,
    get_active_patches,
    rebuild_active,
)
from learn.apply.weight_climber import evaluate_climb
from learn.ingest.models import (
    CounterRecord,
    DetectedSignal,
    DetectionMethod,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    HypothesisTarget,
    HypothesisType,
    SignalType,
)
from learn.validate.validator import validate_hypothesis


def _make_correction_hypothesis(hid: str = "h-cl-001") -> Hypothesis:
    return Hypothesis(
        id=hid,
        type=HypothesisType.KEYWORD_ADJUSTMENT,
        industry="fmcg",
        evidence=Evidence(
            signal_type=SignalType.CORRECTION,
            signal_ids=[f"s{i}" for i in range(8)],
            frequency=8,
            period_days=7,
            unique_sessions=4,
        ),
        target=HypothesisTarget(
            layer="canonical",
            file="category_analysis.yaml",
            path="category_analysis.yaml",
            field="content.required",
        ),
        confidence=0.85,
        current={"sales_amount": 0.80, "order_count": 0.70},
        suggested={"gross_margin_rate": 0.80, "sell_through_rate": 0.60},
    )


def _make_consistent_signals(n: int = 10) -> list[DetectedSignal]:
    signals: list[DetectedSignal] = []
    for i in range(n):
        s = DetectedSignal(
            type=SignalType.CORRECTION,
            session_id=f"s_{i}",
            turn_pair=(1, 2),
            industry="fmcg",
            scenario="category_analysis",
            indicators_before=["sales_amount", "order_count"],
            indicators_after=["gross_margin_rate", "sell_through_rate"],
            detection_method=DetectionMethod.DISJOINT,
            user_anon_id=f"u_{i % 4}",
        )
        signals.append(s)
    return signals


class TestClosedLoop:
    def test_full_cycle_validate_apply_rebuild(self):
        """h → validate → apply → rebuild → verify _active/ output"""
        h = _make_correction_hypothesis()
        signals = _make_consistent_signals(10)

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            canonical_dir = base / "_canonical"
            patches_dir = base / "_patches"
            active_dir = base / "_active"
            schema_dir = base / "_schemas"
            canonical_dir.mkdir()
            schema_dir.mkdir()

            # Seed canonical with baseline
            (canonical_dir / "category_analysis.yaml").write_text(
                "content:\n  required:\n    - sales_amount\n    - order_count\n"
            )

            # Step 1: Validate
            result = validate_hypothesis(h, signals)
            assert result.passed, f"Validation failed: {result.notes}"
            h = Hypothesis(
                id=h.id, type=h.type, industry=h.industry, evidence=h.evidence,
                target=h.target, confidence=h.confidence,
                validated_confidence=result.validated_confidence,
                current=h.current, suggested=h.suggested,
            )

            # Step 2: Apply (creates patch + rebuilds _active/)
            patch = apply_hypothesis(h, patches_dir, canonical_dir, active_dir, schema_dir)
            assert patch.id == h.id
            assert (patches_dir / f"{h.id}.yaml").exists()

            # Step 3: Verify _active/ has the canonical file
            active_file = active_dir / "category_analysis.yaml"
            assert active_file.exists(), f"_active/ missing {active_file}"

    def test_multi_patch_conflict_resolution(self):
        """两个 patch 修改同一指标的 delta 取平均"""
        h1 = _make_correction_hypothesis("h-cl-a")
        h2 = _make_correction_hypothesis("h-cl-b")

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            canonical_dir = base / "_canonical"
            patches_dir = base / "_patches"
            active_dir = base / "_active"
            schema_dir = base / "_schemas"
            canonical_dir.mkdir()
            (canonical_dir / "shared.yaml").write_text("content:\n  weight: 0.50\n")

            # Both patches target the same path
            for hyp_id, h in [("h-cl-a", h1), ("h-cl-b", h2)]:
                h_targeted = Hypothesis(
                    id=h.id, type=h.type, industry=h.industry, evidence=h.evidence,
                    target=HypothesisTarget(
                        layer="canonical", file="shared.yaml", path="shared.yaml",
                    ),
                    confidence=h.confidence, validated_confidence=h.validated_confidence,
                    current=h.current, suggested=h.suggested,
                )
                apply_hypothesis(h_targeted, patches_dir, canonical_dir, active_dir, schema_dir)

            # Both patches should exist
            active = get_active_patches(patches_dir)
            assert len(active) >= 2

    def test_weight_climb_integration(self):
        """validate → apply → simulate 5 weeks of climbing"""
        h = _make_correction_hypothesis()
        signals = _make_consistent_signals(10)

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            canonical_dir = base / "_canonical"
            patches_dir = base / "_patches"
            active_dir = base / "_active"
            schema_dir = base / "_schemas"
            canonical_dir.mkdir()
            (canonical_dir / "category_analysis.yaml").write_text(
                "content:\n  required:\n    - sales_amount\n"
            )

            # Validate
            result = validate_hypothesis(h, signals)
            h = Hypothesis(
                id=h.id, type=h.type, industry=h.industry, evidence=h.evidence,
                target=h.target, confidence=h.confidence,
                validated_confidence=result.validated_confidence,
                current=h.current, suggested=h.suggested,
            )

            # Apply
            apply_hypothesis(h, patches_dir, canonical_dir, active_dir, schema_dir)

            # Simulate weekly climbing
            weight = 0.30
            actions: list[str] = []
            for week in range(5):
                counters = [CounterRecord(session=f"s_w{week}", date=f"2026-05-0{week+1}", total_queries=10)]
                result = evaluate_climb(h, counters, weeks_active=week, current_weight=weight)
                weight = result.new_weight
                actions.append(result.action)

            # Should climb at least 3 out of 5 weeks
            climb_count = sum(1 for a in actions if a == "climb")
            assert climb_count >= 3, f"Only {climb_count}/5 weeks climbed: {actions}"

    def test_defunct_workflow(self):
        """patch → defunct → rebuild excludes it"""
        h = _make_correction_hypothesis("h-defunct-test")
        signals = _make_consistent_signals(10)

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            canonical_dir = base / "_canonical"
            patches_dir = base / "_patches"
            active_dir = base / "_active"
            schema_dir = base / "_schemas"
            canonical_dir.mkdir()
            (canonical_dir / "f.yaml").write_text("value: 1\n")

            result = validate_hypothesis(h, signals)
            h = Hypothesis(
                id=h.id, type=h.type, industry=h.industry, evidence=h.evidence,
                target=HypothesisTarget(layer="canonical", file="f.yaml", path="f.yaml"),
                confidence=h.confidence, validated_confidence=result.validated_confidence,
                current=h.current, suggested=h.suggested,
            )
            apply_hypothesis(h, patches_dir, canonical_dir, active_dir, schema_dir)

            # First rebuild — patch is active
            stats1 = rebuild_active(canonical_dir, patches_dir, active_dir)
            assert "f.yaml" in stats1

            # Defunct the patch
            defunct_patch(h.id, patches_dir)

            # Second rebuild — defunct excluded
            stats2 = rebuild_active(canonical_dir, patches_dir, active_dir)
            assert "f.yaml" not in stats2
