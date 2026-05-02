"""E2E Hook 测试

验证 analyze-observe 和 session-summary 脚本的文件 I/O 副作用。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _setup_hook_env(tmp: str, hook_name: str) -> Path:
    """创建临时项目结构，复制 hook 脚本，返回 hooks 目录路径

    session-summary 内联 Python 需要通过 sys.path 找到 learn 包。
    在 {tmp}/learn/ 下为每个 Python 子包建立 symlink。
    """
    learn_dir = Path(tmp) / "learn"
    hooks_dir = learn_dir / "hooks"
    hooks_dir.mkdir(parents=True)

    src = PROJECT_ROOT / "learn" / "hooks" / hook_name
    dst = hooks_dir / hook_name
    shutil.copy(src, dst)
    dst.chmod(0o755)

    (learn_dir / "data" / "observations" / "sessions").mkdir(parents=True)
    (learn_dir / "data" / "observations" / "skill_calls").mkdir(parents=True)
    (learn_dir / "data" / "signals").mkdir(parents=True)
    (learn_dir / "data" / "counters").mkdir(parents=True)

    # Symlink Python 子包到临时 learn/ 目录
    for pkg in ["ingest", "analyze", "apply", "validate", "monitor"]:
        target = learn_dir / pkg
        if not target.exists():
            target.symlink_to(PROJECT_ROOT / "learn" / pkg, target_is_directory=True)
    init = learn_dir / "__init__.py"
    if not init.exists():
        init.symlink_to(PROJECT_ROOT / "learn" / "__init__.py")

    return hooks_dir


def _run_hook(hooks_dir: Path, hook_name: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """执行 hook 脚本"""
    hook_env = {
        **os.environ,
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(PROJECT_ROOT),
        "CLAUDE_TOOL_NAME": "",
        "CLAUDE_TOOL_INPUT": "",
        "CLAUDE_SESSION_ID": "e2e-test-session",
        "CLAUDE_USER_ID": "e2e-user",
    }
    if env:
        hook_env.update(env)

    return subprocess.run(
        ["bash", str(hooks_dir / hook_name)],
        env=hook_env,
        capture_output=True, text=True,
        timeout=30,
    )


# ============================================================
# analyze-observe
# ============================================================


class TestAnalyzeObserveE2E:
    def test_produces_observation_jsonl(self):
        """E2E-H1: Skill 调用时产生合法 Observation JSONL"""
        with tempfile.TemporaryDirectory() as tmp:
            hooks_dir = _setup_hook_env(tmp, "analyze-observe")
            obs_file = Path(tmp) / "learn" / "data" / "observations" / "sessions" / "e2e-test-session.jsonl"

            result = _run_hook(hooks_dir, "analyze-observe", env={
                "CLAUDE_TOOL_NAME": "Skill",
                "CLAUDE_TOOL_INPUT": "Skill: data-query 查询上个月销售额",
            })

            assert result.returncode == 0
            assert obs_file.exists(), f"Expected {obs_file} to exist"

            lines = obs_file.read_text().strip().splitlines()
            assert len(lines) >= 1

            obs = json.loads(lines[0])
            assert obs["version"] == 2
            assert obs["session_id"] == "e2e-test-session"
            assert obs["industry"] in ("general", "ecommerce", "finance", "logistics", "manufacturing")
            assert "context" in obs
            assert "time_period" in obs["context"]
            assert "trigger_source" in obs["context"]
            assert obs["user_anon_id"] != ""

    def test_non_skill_tool_exits_early(self):
        """E2E-H2: 非 Skill 工具调用不产生记录"""
        with tempfile.TemporaryDirectory() as tmp:
            hooks_dir = _setup_hook_env(tmp, "analyze-observe")
            obs_file = Path(tmp) / "learn" / "data" / "observations" / "sessions" / "e2e-test-session.jsonl"

            result = _run_hook(hooks_dir, "analyze-observe", env={
                "CLAUDE_TOOL_NAME": "Read",
                "CLAUDE_TOOL_INPUT": "read some file",
            })

            assert result.returncode == 0
            assert not obs_file.exists()

    def test_multiple_calls_append(self):
        """E2E-H3: 多次调用追加写入"""
        with tempfile.TemporaryDirectory() as tmp:
            hooks_dir = _setup_hook_env(tmp, "analyze-observe")
            obs_file = Path(tmp) / "learn" / "data" / "observations" / "sessions" / "e2e-test-session.jsonl"

            for i in range(3):
                result = _run_hook(hooks_dir, "analyze-observe", env={
                    "CLAUDE_TOOL_NAME": "Skill",
                    "CLAUDE_TOOL_INPUT": f"Skill: data-analysis 分析第{i}轮",
                })
                assert result.returncode == 0

            lines = obs_file.read_text().strip().splitlines()
            assert len(lines) == 3

            for i, line in enumerate(lines):
                obs = json.loads(line)
                assert obs["turn"] == i  # turn number increments

    def test_infers_time_period_from_query(self):
        """E2E-H4: 从查询文本推断时间周期"""
        with tempfile.TemporaryDirectory() as tmp:
            hooks_dir = _setup_hook_env(tmp, "analyze-observe")
            obs_file = Path(tmp) / "learn" / "data" / "observations" / "sessions" / "e2e-test-session.jsonl"

            _run_hook(hooks_dir, "analyze-observe", env={
                "CLAUDE_TOOL_NAME": "Skill",
                "CLAUDE_TOOL_INPUT": "Skill: data-query 月底盘点销售数据",
            })

            obs = json.loads(obs_file.read_text().strip().splitlines()[0])
            assert obs["context"]["time_period"] == "month_end"

    def test_infers_trigger_source_correction(self):
        """E2E-H5: 纠正类查询推断为 correction"""
        with tempfile.TemporaryDirectory() as tmp:
            hooks_dir = _setup_hook_env(tmp, "analyze-observe")
            obs_file = Path(tmp) / "learn" / "data" / "observations" / "sessions" / "e2e-test-session.jsonl"

            _run_hook(hooks_dir, "analyze-observe", env={
                "CLAUDE_TOOL_NAME": "Skill",
                "CLAUDE_TOOL_INPUT": "Skill: data-query 不对，改成毛利率",
            })

            obs = json.loads(obs_file.read_text().strip().splitlines()[0])
            assert obs["context"]["trigger_source"] == "correction"


# ============================================================
# session-summary
# ============================================================


class TestSessionSummaryE2E:
    def _write_observations(self, tmp: str, observations: list[dict]) -> Path:
        """向临时目录写入 observation JSONL"""
        obs_file = Path(tmp) / "learn" / "data" / "observations" / "sessions" / "e2e-test-session.jsonl"
        with open(obs_file, "w") as f:
            for obs in observations:
                f.write(json.dumps(obs) + "\n")
        return obs_file

    def test_processes_observations_and_writes_signals(self):
        """E2E-S1: 从 observation 产生 signal JSONL 和 counter"""
        with tempfile.TemporaryDirectory() as tmp:
            hooks_dir = _setup_hook_env(tmp, "session-summary")

            # Write two observations: first has indicators, second replaces one
            self._write_observations(tmp, [
                {
                    "version": 2, "ts": "2026-05-01T10:00:00Z", "session_id": "e2e-test-session",
                    "turn": 0, "query": "查销售额", "industry": "fmcg",
                    "source": "l2_match", "indicators_retrieved": ["sales_amount", "order_count"],
                    "scenarios_retrieved": ["sales_trend"], "models_retrieved": [],
                    "analysis_type": "descriptive", "skill_chain_planned": ["data-query"],
                    "skill_chain_actual": ["data-query"], "indicators_candidates": [],
                    "template_matched": None, "user_anon_id": "abc123", "error": None,
                    "context": {"time_period": "normal", "query_raw": "查销售额",
                                "trigger_source": "new_query", "query_intent_hint": None},
                },
                {
                    "version": 2, "ts": "2026-05-01T10:05:00Z", "session_id": "e2e-test-session",
                    "turn": 1, "query": "换成毛利率", "industry": "fmcg",
                    "source": "l2_match", "indicators_retrieved": ["gross_margin_rate"],
                    "scenarios_retrieved": ["sales_trend"], "models_retrieved": [],
                    "analysis_type": "descriptive", "skill_chain_planned": ["data-query", "data-analysis"],
                    "skill_chain_actual": ["data-query", "data-analysis"],
                    "indicators_candidates": [], "template_matched": None,
                    "user_anon_id": "abc123", "error": None,
                    "context": {"time_period": "normal", "query_raw": "换成毛利率",
                                "trigger_source": "correction", "query_intent_hint": None},
                },
            ])

            result = _run_hook(hooks_dir, "session-summary")

            assert result.returncode == 0
            assert "Signals detected" in result.stdout

            # Verify signals JSONL exists
            signals_dir = Path(tmp) / "learn" / "data" / "signals"
            signal_files = list(signals_dir.glob("*.jsonl"))
            assert len(signal_files) > 0

            # Verify counter JSON exists
            counters_dir = Path(tmp) / "learn" / "data" / "counters"
            counter_files = list(counters_dir.glob("*.jsonl"))
            assert len(counter_files) > 0

    def test_empty_observations_graceful(self):
        """E2E-S2: 无 observation 时优雅退出"""
        with tempfile.TemporaryDirectory() as tmp:
            hooks_dir = _setup_hook_env(tmp, "session-summary")

            result = _run_hook(hooks_dir, "session-summary")

            assert result.returncode == 0
            assert "No observations" in result.stdout

    def test_corrupted_jsonl_line_skipped(self):
        """E2E-S3: 损坏的 JSONL 行被跳过"""
        with tempfile.TemporaryDirectory() as tmp:
            hooks_dir = _setup_hook_env(tmp, "session-summary")

            obs_file = Path(tmp) / "learn" / "data" / "observations" / "sessions" / "e2e-test-session.jsonl"
            with open(obs_file, "w") as f:
                f.write("this is not valid json\n")
                f.write(json.dumps({
                    "version": 2, "ts": "2026-05-01T10:00:00Z",
                    "session_id": "e2e-test-session", "turn": 0, "query": "查销售",
                    "industry": "fmcg", "source": "l2_match",
                    "indicators_retrieved": ["sales_amount"],
                    "scenarios_retrieved": ["sales_trend"], "models_retrieved": [],
                    "analysis_type": "descriptive", "skill_chain_planned": ["data-query"],
                    "skill_chain_actual": ["data-query"], "indicators_candidates": [],
                    "template_matched": None, "user_anon_id": "abc", "error": None,
                    "context": {"time_period": "normal", "query_raw": "查销售",
                                "trigger_source": "new_query", "query_intent_hint": None},
                }) + "\n")

            result = _run_hook(hooks_dir, "session-summary")

            # Should not crash; processes the valid line
            assert result.returncode == 0
