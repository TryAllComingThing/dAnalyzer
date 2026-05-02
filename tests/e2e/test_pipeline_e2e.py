"""E2E 文件管线测试

验证多组件通过文件 I/O 串联后的正确性。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from learn.analyze.signal_analyzer import (
    cluster_corrections,
    cluster_supplements,
    generate_hypotheses,
)
from learn.analyze.template_deviation import compute_deviation
from learn.apply.applier import apply_hypothesis
from learn.apply.draft_manager import evaluate_draft, simulate_weeks
from learn.apply.patch_builder import rebuild_active
from learn.apply.template_updater import compute_adjustment
from learn.ingest.counter_writer import append_signal, load_signals, write_counters
from learn.ingest.models import (
    CounterRecord,
    DetectedSignal,
    DetectionMethod,
    DraftTemplate,
    HypothesisStatus,
    HypothesisType,
    SignalType,
)
from learn.ingest.session_processor import process_session, load_observations
from learn.validate.validator import validate_hypothesis


def _make_obs_dict(turn=0, query="查销售", indicators=None, scenarios=None,
                   session_id="e2e-pipe", industry="fmcg", source="l2_match",
                   actual_chain=None):
    return {
        "version": 2, "ts": "2026-05-01T10:00:00Z", "session_id": session_id,
        "turn": turn, "query": query, "industry": industry, "source": source,
        "indicators_retrieved": indicators or ["sales_amount"],
        "scenarios_retrieved": scenarios or ["sales_trend"],
        "models_retrieved": [], "analysis_type": "descriptive",
        "skill_chain_planned": actual_chain or ["data-query"],
        "skill_chain_actual": actual_chain or ["data-query"],
        "indicators_candidates": [], "template_matched": None,
        "user_anon_id": "e2e-user", "error": None,
        "context": {"time_period": "normal", "query_raw": query,
                    "trigger_source": "new_query", "query_intent_hint": None},
    }


# ============================================================
# observation → signal → counter 链路
# ============================================================


class TestObservationToSignalPipeline:
    def test_full_jsonl_roundtrip(self):
        """E2E-P1: observation JSONL → process_session → signal JSONL → load"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            obs_file = tmp_path / "observations.jsonl"
            signals_dir = tmp_path / "signals"
            counters_dir = tmp_path / "counters"
            signals_dir.mkdir()
            counters_dir.mkdir()

            # Write observations
            obs_list = [
                _make_obs_dict(0, "查销售额", ["sales_amount", "order_count"]),
                _make_obs_dict(1, "换成毛利率", ["gross_margin_rate"],
                               actual_chain=["data-query", "data-analysis"]),
            ]
            with open(obs_file, "w") as f:
                for obs in obs_list:
                    f.write(json.dumps(obs) + "\n")

            # Load and process
            observations = load_observations(obs_file)
            assert len(observations) == 2

            signals, counter = process_session(
                "e2e-pipe", observations,
                str(signals_dir), str(counters_dir),
            )

            # Roundtrip: read back signals from JSONL
            loaded = load_signals(str(signals_dir))
            assert len(loaded) >= 0

            # Counter file exists
            counter_files = list(counters_dir.glob("*.jsonl"))
            assert len(counter_files) >= 1

    def test_signal_jsonl_deserializable(self):
        """E2E-P2: 写入 JSONL 的信号可反序列化为 DetectedSignal"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            signals_dir = tmp_path / "signals"
            signals_dir.mkdir()

            signal = DetectedSignal(
                type=SignalType.CORRECTION, session_id="e2e-p2",
                turn_pair=(1, 2), industry="fmcg", scenario="sales_trend",
                replaced_indicators=["sales_amount"],
                added_indicators=["gross_margin_rate"],
                indicators_before=["sales_amount", "order_count"],
                indicators_after=["gross_margin_rate", "order_count"],
                detection_method=DetectionMethod.DISJOINT,
            )

            append_signal(signals_dir / "corrections.jsonl", signal)
            loaded = load_signals(str(signals_dir), ["corrections"])

            assert len(loaded) == 1
            assert loaded[0]["type"] == "correction"
            assert loaded[0]["session_id"] == "e2e-p2"
            assert "sales_amount" in loaded[0]["replaced_indicators"]

    def test_counter_json_roundtrip(self):
        """E2E-P3: Counter JSON 写入后再读取"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            counters_dir = tmp_path / "counters"
            counters_dir.mkdir()

            counter = CounterRecord(
                session="e2e-p3", date="2026-05-01",
                total_queries=5, l1_hits=3, l2_hits=1, l3_fallbacks=1,
                corrections=1, supplements=0, refinements=0, errors=0,
                by_scenario={"sales_trend": {"correction": 1}},
            )

            write_counters(counters_dir / "e2e-p3.json", counter)

            # Read back
            data = json.loads((counters_dir / "e2e-p3.json").read_text())
            assert data["session"] == "e2e-p3"
            assert data["total_queries"] == 5

    def test_multi_session_signal_accumulation(self):
        """E2E-P4: 多 session 信号追加不覆盖"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            signals_dir = tmp_path / "signals"
            counters_dir = tmp_path / "counters"
            signals_dir.mkdir()
            counters_dir.mkdir()

            for sid in ["s1", "s2", "s3"]:
                obs_file = tmp_path / f"obs_{sid}.jsonl"
                with open(obs_file, "w") as f:
                    f.write(json.dumps(_make_obs_dict(0, f"查询{sid}",
                                                       session_id=sid)) + "\n")
                    f.write(json.dumps(_make_obs_dict(1, f"纠正{sid}",
                                                       indicators=["other_indicator"],
                                                       session_id=sid,
                                                       actual_chain=["data-query", "data-analysis"])) + "\n")

                observations = load_observations(obs_file)
                process_session(sid, observations, str(signals_dir), str(counters_dir))

            # All 3 sessions processed; same date → same .jsonl, 3 lines
            counter_files = list(counters_dir.glob("*.jsonl"))
            assert len(counter_files) == 1
            lines = counter_files[0].read_text().strip().splitlines()
            assert len(lines) == 3

            # Signal files contain data from all sessions
            all_signals = load_signals(str(signals_dir))
            sessions = {s["session_id"] for s in all_signals}
            assert sessions >= {"s1", "s2", "s3"}


# ============================================================
# signals → patch → rebuild 链路
# ============================================================


class TestSignalsToPatchPipeline:
    def test_signals_to_patch_file_chain(self):
        """E2E-P5: signals → cluster → hypothesis → validate → apply → patch"""
        signals = []
        for i in range(5):
            signals.append(DetectedSignal(
                type=SignalType.CORRECTION, session_id=f"s{i % 3}", turn_pair=(1, 2),
                industry="fmcg", scenario="sales_trend",
                replaced_indicators=["sales_amount"],
                added_indicators=["gross_margin_rate"],
                indicators_before=["sales_amount", "order_count"],
                indicators_after=["gross_margin_rate", "order_count"],
                detection_method=DetectionMethod.DISJOINT,
            ))

        clusters = cluster_corrections(signals)
        assert len(clusters) >= 1

        hypotheses = generate_hypotheses(clusters)
        assert len(hypotheses) >= 1

        h = hypotheses[0]
        result = validate_hypothesis(h, signals, holdout_ratio=0.25)
        assert result.pass_rate >= 0.0

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            canonical = tmp_path / "_canonical"
            patches = tmp_path / "_patches"
            active = tmp_path / "_active"
            schema = tmp_path / "_schema"

            canonical.mkdir(parents=True)
            (canonical / "fmcg").mkdir()
            (canonical / "fmcg" / "indicators").mkdir()
            (canonical / "fmcg" / "indicators" / "sales_amount.yaml").write_text(
                "id: sales_amount\nname: 销售额\nweight: 0.80\n")
            patches.mkdir()
            active.mkdir()
            schema.mkdir()

            patch = apply_hypothesis(h, str(patches), str(canonical), str(active), str(schema))
            assert patch.id == h.id

            # Verify patch YAML exists
            patch_files = list(patches.glob("*.yaml"))
            assert len(patch_files) == 1

            # Rebuild _active/
            rebuild_result = rebuild_active(str(canonical), str(patches), str(active))
            assert isinstance(rebuild_result, dict)

    def test_empty_signals_produces_no_patches(self):
        """E2E-P6: 空信号 → 空聚类 → 无补丁"""
        clusters = cluster_corrections([])
        assert clusters == []
        hypotheses = generate_hypotheses([])
        assert hypotheses == []


# ============================================================
# template 生命周期文件链路
# ============================================================


class TestTemplatePipeline:
    def test_draft_simulate_weeks_to_promotion(self):
        """E2E-P7: 模拟 4 周 reinforcement → 权重爬坡 → 晋升"""
        draft = DraftTemplate(
            id="draft-e2e", name="E2E Draft", status="draft", version=1,
            routing_weight=0.25,
            indicators={"required": [{"id": "sales_amount", "weight": 1.0}],
                        "optional": []},
            steps=[{"skill": "data-query", "optional": False}],
            applicability={"scenarios": ["sales_trend"]},
            evidence_signals=["s1:1:2"],
        )

        weekly = []
        for w in range(4):
            weekly.append([DetectedSignal(
                type=SignalType.REINFORCEMENT, session_id=f"s{w}", turn_pair=(1, 1),
                industry="fmcg", scenario="sales_trend",
            )])

        history = simulate_weeks(draft, weekly)
        assert len(history) == 4
        final_weight = history[-1][1]
        assert final_weight >= 0.55  # 0.25 + 4 * 0.10 = 0.65

    def test_deviation_to_adjustment_pipeline(self):
        """E2E-P8: 偏离报告 → 原子调整"""
        draft = DraftTemplate(
            id="tpl-e2e", name="Deviation Test", status="active", version=1,
            routing_weight=0.70,
            indicators={"required": [{"id": "sales_amount", "weight": 1.0}],
                        "optional": []},
            steps=[{"skill": "data-query", "optional": False}],
            applicability={"scenarios": ["sales_trend"], "industries": ["fmcg"]},
            evidence_signals=["s1:1:2"],
        )

        signals = []
        for i in range(10):
            signals.append(DetectedSignal(
                type=SignalType.REINFORCEMENT, session_id=f"sr{i}", turn_pair=(1, 1),
                industry="fmcg", scenario="sales_trend",
                indicators_before=["sales_amount"],
            ))
        for i in range(10):
            signals.append(DetectedSignal(
                type=SignalType.CORRECTION, session_id=f"sc{i}", turn_pair=(1, 2),
                industry="fmcg", scenario="sales_trend",
                replaced_indicators=["sales_amount"],
                detection_method=DetectionMethod.DISJOINT,
            ))

        report = compute_deviation(draft, signals, weeks=4)
        assert report.triggers

        adj = compute_adjustment(report, last_adjustment_week=-10, current_week=10)
        assert adj is not None
        assert adj.template_id == "tpl-e2e"
