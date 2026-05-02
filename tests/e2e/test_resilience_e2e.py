"""E2E 异常路径测试

验证边界条件和容错行为。
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from learn.analyze.template_discovery import discover_templates
from learn.apply.patch_builder import rebuild_active
from learn.ingest.counter_writer import append_signal, load_signals
from learn.ingest.models import DetectedSignal, DetectionMethod, SignalType
from learn.monitor.health_metrics import compute_48h_metrics, compute_weekly_report
from learn.monitor.anomaly_detector import (
    check_degradation,
    check_signal_burst,
    check_single_user_dominance,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ============================================================
# intent_parser 容错
# ============================================================


class TestIntentParserResilience:
    def test_missing_data_root_graceful(self):
        """E2E-R1: 知识目录不存在时降级到 L3"""
        result = subprocess.run(
            ["python3", str(PROJECT_ROOT / "scripts" / "intent_parser.py"),
             "--query", "品类分析", "--data_root", "nonexistent/path/xyz"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["source"] == "l3_llm_fallback"

    def test_empty_query_produces_result(self):
        """E2E-R2: 空查询不崩溃"""
        result = subprocess.run(
            ["python3", str(PROJECT_ROOT / "scripts" / "intent_parser.py"),
             "--query", "", "--industry", "fmcg"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "source" in data


# ============================================================
# patch_builder 容错
# ============================================================


class TestPatchBuilderResilience:
    def test_empty_patches_dir_rebuild(self):
        """E2E-R3: 无 patches 时 rebuild 仅复制 canonical → _active/"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            canonical = tmp_path / "_canonical"
            patches = tmp_path / "_patches"
            active = tmp_path / "_active"

            canonical.mkdir(parents=True)
            (canonical / "fmcg" / "indicators").mkdir(parents=True)
            (canonical / "fmcg" / "indicators" / "test.yaml").write_text(
                "id: test\nname: Test\nweight: 1.0\n")

            patches.mkdir()
            active.mkdir()

            result = rebuild_active(str(canonical), str(patches), str(active))
            assert isinstance(result, dict)

            # _active/ should contain the copied file
            active_file = active / "fmcg" / "indicators" / "test.yaml"
            assert active_file.exists()

    def test_missing_canonical_dir_handled(self):
        """E2E-R4: canonical 目录缺失时 rebuild 不崩溃"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            canonical = tmp_path / "_canonical_nonexistent"
            patches = tmp_path / "_patches"
            active = tmp_path / "_active"
            patches.mkdir()
            active.mkdir()

            result = rebuild_active(str(canonical), str(patches), str(active))
            # Empty result — nothing to copy
            assert isinstance(result, dict)


# ============================================================
# signal loading 容错
# ============================================================


class TestSignalLoadingResilience:
    def test_load_from_empty_dir(self):
        """E2E-R5: 空目录加载信号返回空列表"""
        with tempfile.TemporaryDirectory() as tmp:
            loaded = load_signals(tmp, list(SignalType))
            assert loaded == []

    def test_load_from_missing_dir(self):
        """E2E-R6: 不存在目录加载信号返回空列表"""
        loaded = load_signals("/tmp/nonexistent_signals_dir_xyz", list(SignalType))
        assert loaded == []


# ============================================================
# 监控容错
# ============================================================


class TestMonitorResilience:
    def test_metrics_with_empty_counters(self):
        """E2E-R7: 空计数器 → 指标归零，不崩溃"""
        from learn.ingest.models import CounterRecord

        window = compute_48h_metrics("sales_trend", [], [])
        assert window.query_count == 0
        assert not window.sufficient_samples
        assert not window.l3_degradation

        weekly = compute_weekly_report("2026-01-01", [])
        assert weekly.total_queries == 0
        assert weekly.health_status == "healthy"

    def test_anomaly_with_empty_signals(self):
        """E2E-R8: 空信号 → 异常检测返回 False"""
        assert not check_single_user_dominance([])
        assert not check_signal_burst([])

    def test_metrics_with_zero_queries(self):
        """E2E-R9: 零查询 counter → 指标为 0"""
        from learn.ingest.models import CounterRecord

        counter = CounterRecord(
            session="empty", date="2026-01-01",
            total_queries=0, l1_hits=0, l2_hits=0, l3_fallbacks=0,
            corrections=0, supplements=0, refinements=0, errors=0,
            by_scenario={},
        )

        window = compute_48h_metrics("sales_trend", [counter], [counter])
        assert window.query_count == 0
        assert window.l3_rate == 0.0


# ============================================================
# template discovery 容错
# ============================================================


class TestTemplateDiscoveryResilience:
    def test_empty_signals_no_drafts(self):
        """E2E-R10: 空扩展信号 → 无草稿"""
        drafts = discover_templates([], [])
        assert drafts == []

    def test_no_extension_signals_no_drafts(self):
        """E2E-R11: 有信号但无 extension → 无草稿"""
        signals = [
            DetectedSignal(
                type=SignalType.CORRECTION, session_id="s1", turn_pair=(1, 2),
                industry="fmcg", scenario="sales_trend",
                detection_method=DetectionMethod.DISJOINT,
            ),
        ]
        drafts = discover_templates(signals, [])
        assert drafts == []
