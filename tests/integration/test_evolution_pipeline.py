"""Phase 2 集成测试 — 端到端信号检测管道

用测试夹具的 5-turn session 跑完整链路，验证所有 JSONL 输出正确。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from learn.ingest.counter_writer import load_signals
from learn.ingest.models import SignalType
from learn.ingest.session_processor import process_session
from tests.fixtures.evolution_fixtures import (
    make_correction_pair,
    make_five_turn_session,
    make_partial_correction_pair,
    make_supplement_pair,
)


class TestEndToEndPipeline:
    def test_five_turn_session_produces_signals(self):
        observations = make_five_turn_session()
        assert len(observations) == 5

        with tempfile.TemporaryDirectory() as signals_d, tempfile.TemporaryDirectory() as counters_d:
            signals, counter = process_session(
                session_id="test-session-001",
                observations=observations,
                signals_dir=signals_d,
                counters_dir=counters_d,
            )

            assert len(signals) > 0, "Should produce at least one signal"
            assert counter.total_queries == 5

    def test_correction_written_to_jsonl(self):
        observations = make_five_turn_session()[:2]  # correction pair

        with tempfile.TemporaryDirectory() as signals_d, tempfile.TemporaryDirectory() as counters_d:
            signals, _ = process_session(
                session_id="s-001",
                observations=observations,
                signals_dir=signals_d,
                counters_dir=counters_d,
            )

            corrections = [s for s in signals if s.type == SignalType.CORRECTION]
            assert len(corrections) == 1

            loaded = load_signals(signals_d, ["corrections"])
            assert len(loaded) == 1
            assert loaded[0]["type"] == "correction"
            assert loaded[0]["session_id"] == "s-001"

    def test_supplement_written_to_jsonl(self):
        prev, curr = make_supplement_pair()

        with tempfile.TemporaryDirectory() as signals_d, tempfile.TemporaryDirectory() as counters_d:
            signals, _ = process_session(
                session_id="s-002",
                observations=[prev, curr],
                signals_dir=signals_d,
                counters_dir=counters_d,
            )

            supplements = [s for s in signals if s.type == SignalType.SUPPLEMENT]
            assert len(supplements) == 1

            loaded = load_signals(signals_d, ["supplements"])
            assert len(loaded) == 1
            assert loaded[0]["type"] == "supplement"

    def test_counterfactual_via_user_selections(self):
        from tests.fixtures.evolution_fixtures import make_counterfactual_observation
        obs = make_counterfactual_observation()

        with tempfile.TemporaryDirectory() as signals_d, tempfile.TemporaryDirectory() as counters_d:
            signals, _ = process_session(
                session_id="s-cf-001",
                observations=[obs],
                signals_dir=signals_d,
                counters_dir=counters_d,
                user_selections={2: ["gross_margin_rate", "sell_through_rate"]},
            )

            cf_signals = [s for s in signals if s.type == SignalType.COUNTERFACTUAL]
            assert len(cf_signals) == 1
            assert cf_signals[0].candidate_hit is True

    def test_preference_signals_written(self):
        from tests.fixtures.evolution_fixtures import make_preference_observation_chart
        obs = make_preference_observation_chart()

        with tempfile.TemporaryDirectory() as signals_d, tempfile.TemporaryDirectory() as counters_d:
            signals, _ = process_session(
                session_id="s-pref-001",
                observations=[obs],
                signals_dir=signals_d,
                counters_dir=counters_d,
                chart_choices={3: ("heatmap", "line_chart")},
            )

            pref_signals = [s for s in signals if s.type == SignalType.PREFERENCE_CHART]
            assert len(pref_signals) == 1

            loaded = load_signals(signals_d, ["preferences"])
            assert len(loaded) == 1

    def test_reinforcement_signals_written(self):
        observations = make_five_turn_session()

        with tempfile.TemporaryDirectory() as signals_d, tempfile.TemporaryDirectory() as counters_d:
            signals, _ = process_session(
                session_id="s-reinf-001",
                observations=observations,
                signals_dir=signals_d,
                counters_dir=counters_d,
            )

            reinf = [s for s in signals if s.type == SignalType.REINFORCEMENT]
            assert len(reinf) > 0

            loaded = load_signals(signals_d, ["reinforcements"])
            assert len(loaded) > 0
            for r in loaded:
                assert r["type"] == "reinforcement"

    def test_counter_aggregation(self):
        observations = make_five_turn_session()

        with tempfile.TemporaryDirectory() as signals_d, tempfile.TemporaryDirectory() as counters_d:
            _, counter = process_session(
                session_id="s-cnt-001",
                observations=observations,
                signals_dir=signals_d,
                counters_dir=counters_d,
            )

            assert counter.total_queries == 5
            assert counter.l1_hits == 5  # all l1_exact in fixture
            assert counter.l3_fallbacks == 0

    def test_empty_observations_graceful(self):
        with tempfile.TemporaryDirectory() as signals_d, tempfile.TemporaryDirectory() as counters_d:
            signals, counter = process_session(
                session_id="s-empty",
                observations=[],
                signals_dir=signals_d,
                counters_dir=counters_d,
            )
            assert signals == []
            assert counter.total_queries == 0

    def test_partial_correction_pipeline(self):
        prev, curr = make_partial_correction_pair()

        with tempfile.TemporaryDirectory() as signals_d, tempfile.TemporaryDirectory() as counters_d:
            signals, _ = process_session(
                session_id="s-partial",
                observations=[prev, curr],
                signals_dir=signals_d,
                counters_dir=counters_d,
            )

            corrections = [s for s in signals if s.type == SignalType.CORRECTION]
            assert len(corrections) == 1
            assert corrections[0].replacement_ratio >= 0.5
            assert len(corrections[0].kept_indicators) > 0

    def test_reinforcement_only_on_accepted_turns(self):
        """reinforcement 信号不应在纠正 turn 上产生"""
        prev, curr = make_correction_pair()

        with tempfile.TemporaryDirectory() as signals_d, tempfile.TemporaryDirectory() as counters_d:
            signals, _ = process_session(
                session_id="s-corr",
                observations=[prev, curr],
                signals_dir=signals_d,
                counters_dir=counters_d,
            )

            reinf = [s for s in signals if s.type == SignalType.REINFORCEMENT]
            # Turn 2 is last turn (no error) → reinforcement; Turn 1 is correction → no reinforcement
            reinf_turns = [s.turn_pair[0] for s in reinf]
            assert 1 not in reinf_turns, "Correction turn should not get reinforcement"
            assert 2 in reinf_turns, "Last turn should get reinforcement"
