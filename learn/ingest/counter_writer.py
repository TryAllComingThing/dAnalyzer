"""健康计数器写入

Session 结束时原子写入计数器 JSON 和信号 JSONL。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from learn.ingest.models import CounterRecord, DetectedSignal


def append_signal(path: str | Path, signal: DetectedSignal) -> None:
    """原子追加一行信号 JSONL"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    line = json.dumps(_signal_to_dict(signal), ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def write_counters(path: str | Path, counter: CounterRecord) -> None:
    """原子写入计数器 JSON"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temp = path.with_suffix(path.suffix + ".tmp")
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(_counter_to_dict(counter), f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def write_counters_jsonl(
    dir_path: str | Path, date_str: str, counter: CounterRecord
) -> None:
    """追加一行计数器到 {date}.jsonl"""
    dir_path = Path(dir_path)
    file_path = dir_path / f"{date_str}.jsonl"
    append_counter_line(file_path, counter)


def append_counter_line(path: str | Path, counter: CounterRecord) -> None:
    """原子追加一行计数器 JSONL"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    line = json.dumps(_counter_to_dict(counter), ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def load_signals(
    dir_path: str | Path, signal_types: list[str] | None = None
) -> list[dict]:
    """加载指定类型的信号，从 {dir_path}/{type}.jsonl 文件"""
    dir_path = Path(dir_path)
    if signal_types is None:
        signal_types = [
            "corrections",
            "supplements",
            "refinements",
            "extensions",
            "reinforcements",
            "counterfactuals",
            "preferences",
        ]

    results: list[dict] = []
    for st in signal_types:
        fpath = dir_path / f"{st}.jsonl"
        if fpath.exists():
            for line in fpath.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    results.append(json.loads(line))
    return results


def _signal_to_dict(signal: DetectedSignal) -> dict:
    return {
        "type": signal.type.value,
        "session_id": signal.session_id,
        "turn_pair": list(signal.turn_pair),
        "industry": signal.industry,
        "scenario": signal.scenario,
        "ts": signal.ts,
        "indicators_before": signal.indicators_before,
        "indicators_after": signal.indicators_after,
        "template_before": signal.template_before,
        "template_after": signal.template_after,
        "query_before": signal.query_before,
        "query_after": signal.query_after,
        "detection_method": signal.detection_method.value,
        "replacement_ratio": signal.replacement_ratio,
        "replaced_indicators": signal.replaced_indicators,
        "added_indicators": signal.added_indicators,
        "kept_indicators": signal.kept_indicators,
        "candidate_hit": signal.candidate_hit,
        "hit_ranks": signal.hit_ranks,
        "user_anon_id": signal.user_anon_id,
    }


def _counter_to_dict(counter: CounterRecord) -> dict:
    d = {
        "session": counter.session,
        "date": counter.date,
        "total_queries": counter.total_queries,
        "l1_hits": counter.l1_hits,
        "l2_hits": counter.l2_hits,
        "l3_fallbacks": counter.l3_fallbacks,
        "plan_validation_failures": counter.plan_validation_failures,
        "corrections": counter.corrections,
        "supplements": counter.supplements,
        "refinements": counter.refinements,
        "errors": counter.errors,
        "by_scenario": counter.by_scenario,
    }
    return d
