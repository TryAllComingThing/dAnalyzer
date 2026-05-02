"""Phase 4 应用与爬坡模块单元测试

覆盖: applier.apply_hypothesis / patch_builder / weight_climber
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
from learn.apply.weight_climber import batch_evaluate, evaluate_climb
from learn.ingest.models import (
    ClimbResult,
    CounterRecord,
    Evidence,
    Hypothesis,
    HypothesisStatus,
    HypothesisTarget,
    HypothesisType,
    PatchOp,
    PatchOperation,
    SignalType,
)


def _make_hypothesis(
    hid: str = "h-001",
    confidence: float = 0.85,
    current: dict | None = None,
    suggested: dict | None = None,
) -> Hypothesis:
    return Hypothesis(
        id=hid,
        type=HypothesisType.KEYWORD_ADJUSTMENT,
        industry="fmcg",
        evidence=Evidence(
            signal_type=SignalType.CORRECTION,
            signal_ids=["s1", "s2", "s3", "s4"],
            frequency=4,
            period_days=7,
            unique_sessions=3,
        ),
        target=HypothesisTarget(
            layer="canonical",
            file="category_analysis.yaml",
            path="category_analysis.yaml",
            field="content.required",
        ),
        confidence=confidence,
        validated_confidence=confidence,
        current=current or {"sales_amount": 0.80},
        suggested=suggested or {"gross_margin_rate": 0.80},
    )


class TestApplyHypothesis:
    def test_creates_patch_file(self):
        h = _make_hypothesis()
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            canonical_dir = base / "_canonical"
            patches_dir = base / "_patches"
            active_dir = base / "_active"
            schema_dir = base / "_schemas"

            canonical_dir.mkdir()
            # Create a baseline canonical file
            (canonical_dir / "category_analysis.yaml").write_text(
                "content:\n  required:\n    - sales_amount\n    - order_count\n"
            )

            patch = apply_hypothesis(h, patches_dir, canonical_dir, active_dir, schema_dir)

            assert patch.id == "h-001"
            assert patch.validated_confidence == 0.85
            patch_file = patches_dir / f"{h.id}.yaml"
            assert patch_file.exists()

    def test_patch_has_correct_structure(self):
        h = _make_hypothesis()
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            canonical_dir = base / "_canonical"
            patches_dir = base / "_patches"
            active_dir = base / "_active"
            schema_dir = base / "_schemas"
            canonical_dir.mkdir()

            patch = apply_hypothesis(h, patches_dir, canonical_dir, active_dir, schema_dir)

            assert len(patch.operations) >= 1
            assert patch.status in (HypothesisStatus.FULL_APPLIED, HypothesisStatus.PROGRESSIVE)
            assert patch.schema_version == 2

    def test_patch_uses_progressive_for_low_confidence(self):
        h = _make_hypothesis(confidence=0.75)
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            canonical_dir = base / "_canonical"
            patches_dir = base / "_patches"
            active_dir = base / "_active"
            schema_dir = base / "_schemas"
            canonical_dir.mkdir()

            patch = apply_hypothesis(h, patches_dir, canonical_dir, active_dir, schema_dir)
            assert patch.status == HypothesisStatus.PROGRESSIVE

    def test_high_confidence_full_applied(self):
        h = _make_hypothesis(confidence=0.92)
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            canonical_dir = base / "_canonical"
            patches_dir = base / "_patches"
            active_dir = base / "_active"
            schema_dir = base / "_schemas"
            canonical_dir.mkdir()

            patch = apply_hypothesis(h, patches_dir, canonical_dir, active_dir, schema_dir)
            assert patch.status == HypothesisStatus.FULL_APPLIED


class TestPatchBuilder:
    def test_rebuild_with_no_patches_copies_canonical(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            canonical_dir = base / "_canonical"
            patches_dir = base / "_patches"
            active_dir = base / "_active"

            canonical_dir.mkdir()
            (canonical_dir / "test.yaml").write_text("key: value\n")

            stats = rebuild_active(canonical_dir, patches_dir, active_dir)

            assert stats == {}
            active_file = active_dir / "test.yaml"
            assert active_file.exists()

    def test_rebuild_with_single_patch(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            canonical_dir = base / "_canonical"
            patches_dir = base / "_patches"
            active_dir = base / "_active"
            schema_dir = base / "_schemas"

            canonical_dir.mkdir()
            (canonical_dir / "test.yaml").write_text("weight: 0.5\n")

            h = _make_hypothesis(
                current={"sales_amount": 0.80},
                suggested={"gross_margin_rate": 0.80},
            )
            # Must set target path to match canonical
            h = Hypothesis(
                id=h.id, type=h.type, industry=h.industry, evidence=h.evidence,
                target=HypothesisTarget(
                    layer="canonical", file="test.yaml", path="test.yaml",
                ),
                confidence=h.confidence, validated_confidence=h.validated_confidence,
                current=h.current, suggested=h.suggested,
            )

            apply_hypothesis(h, patches_dir, canonical_dir, active_dir, schema_dir)
            assert (active_dir / "test.yaml").exists()

    def test_defunct_patch_excluded_from_rebuild(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            canonical_dir = base / "_canonical"
            patches_dir = base / "_patches"
            active_dir = base / "_active"
            schema_dir = base / "_schemas"

            canonical_dir.mkdir()
            (canonical_dir / "test.yaml").write_text("indicators: [a, b]\n")

            h = _make_hypothesis(
                "h-defunct", current={"sales_amount": 0.80}, suggested={"gross_margin": 0.80},
            )
            h = Hypothesis(
                id=h.id, type=h.type, industry=h.industry, evidence=h.evidence,
                target=HypothesisTarget(
                    layer="canonical", file="test.yaml", path="test.yaml",
                ),
                confidence=h.confidence, validated_confidence=h.validated_confidence,
                current=h.current, suggested=h.suggested,
            )

            apply_hypothesis(h, patches_dir, canonical_dir, active_dir, schema_dir)

            # Defunct it
            result = defunct_patch(h.id, patches_dir)
            assert result is True

            # get_active_patches should not include it
            active = get_active_patches(patches_dir)
            assert all(p["id"] != h.id for p in active)

            # Rebuild — defunct patch excluded
            stats = rebuild_active(canonical_dir, patches_dir, active_dir)
            assert "test.yaml" not in stats  # defunct patch excluded

    def test_get_active_patches(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            canonical_dir = base / "_canonical"
            patches_dir = base / "_patches"
            active_dir = base / "_active"
            schema_dir = base / "_schemas"
            canonical_dir.mkdir()

            h1 = _make_hypothesis("h-p1", current={"a": 1.0}, suggested={"b": 0.80})
            h1 = Hypothesis(
                id=h1.id, type=h1.type, industry=h1.industry, evidence=h1.evidence,
                target=HypothesisTarget(layer="canonical", file="f.yaml", path="f.yaml"),
                confidence=h1.confidence, validated_confidence=h1.validated_confidence,
                current=h1.current, suggested=h1.suggested,
            )
            h2 = _make_hypothesis("h-p2", current={"c": 1.0}, suggested={"d": 0.80})
            h2 = Hypothesis(
                id=h2.id, type=h2.type, industry=h2.industry, evidence=h2.evidence,
                target=HypothesisTarget(layer="canonical", file="f.yaml", path="f.yaml"),
                confidence=h2.confidence, validated_confidence=h2.validated_confidence,
                current=h2.current, suggested=h2.suggested,
            )

            apply_hypothesis(h1, patches_dir, canonical_dir, active_dir, schema_dir)
            apply_hypothesis(h2, patches_dir, canonical_dir, active_dir, schema_dir)

            active = get_active_patches(patches_dir)
            assert len(active) >= 2


class TestWeightClimber:
    def test_climb_on_no_degradation(self):
        h = _make_hypothesis(confidence=0.85)
        counters = [CounterRecord(session="s1", date="2026-05-01", total_queries=5)]
        result = evaluate_climb(h, counters, weeks_active=2)
        assert result.action == "climb"
        assert result.new_weight == 0.45  # 0.30 + 0.15

    def test_freeze_on_degradation(self):
        h = _make_hypothesis(confidence=0.85)
        counters = [CounterRecord(session="s1", date="2026-05-01", total_queries=5, l3_fallbacks=2)]
        result = evaluate_climb(h, counters, weeks_active=1)
        assert result.action == "freeze"
        assert result.weeks_frozen == 1

    def test_decay_after_3_weeks_frozen(self):
        h = _make_hypothesis(confidence=0.85)
        counters = [CounterRecord(session="s1", date="2026-05-01", l3_fallbacks=2)]
        result = evaluate_climb(h, counters, weeks_active=1, weeks_frozen=3)
        assert result.action == "decay"
        assert result.new_weight < 0.30

    def test_defunct_after_8_weeks_frozen(self):
        h = _make_hypothesis(confidence=0.85)
        result = evaluate_climb(h, [], weeks_active=0, weeks_frozen=8)
        assert result.action == "defunct"

    def test_mature_when_weight_above_threshold(self):
        h = _make_hypothesis(confidence=0.85)
        counters = [CounterRecord(session="s1", date="2026-05-01", total_queries=5)]
        result = evaluate_climb(h, counters, weeks_active=4, current_weight=0.80)
        assert result.action == "mature"

    def test_hold_when_no_signals(self):
        h = _make_hypothesis(confidence=0.85)
        result = evaluate_climb(h, [], weeks_active=1)
        assert result.action == "hold"

    def test_climb_sequence_to_mature(self):
        """完整爬坡：0.30 → 0.45 → 0.60 → 0.75 → 0.90 → mature"""
        h = _make_hypothesis(confidence=0.85)
        counters = [CounterRecord(session="s1", date="2026-05-01", total_queries=10)]
        weight = 0.30
        for week in range(5):
            result = evaluate_climb(h, counters, weeks_active=week, current_weight=weight)
            weight = result.new_weight
            if result.action == "mature":
                break
        assert weight >= 0.75 or result.action == "mature"

    def test_batch_evaluate_filters_non_progressive(self):
        h_prog = _make_hypothesis("h-prog", confidence=0.75)
        # Override status to progressive
        from dataclasses import replace
        h_prog = replace(h_prog, status=HypothesisStatus.PROGRESSIVE)

        h_full = _make_hypothesis("h-full", confidence=0.95)
        h_full = replace(h_full, status=HypothesisStatus.FULL_APPLIED)

        counters = [CounterRecord(session="s1", date="2026-05-01", total_queries=5)]
        results = batch_evaluate([h_prog, h_full], counters)
        assert len(results) == 1
        assert results[0].hypothesis_id == "h-prog"
