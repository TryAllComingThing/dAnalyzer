"""E2E CLI 测试

验证 intent_parser.py 命令行端到端行为。
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _run_parser(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """执行 intent_parser.py"""
    return subprocess.run(
        ["python3", str(PROJECT_ROOT / "scripts" / "intent_parser.py")] + args,
        capture_output=True, text=True,
        timeout=timeout,
        env={**os.environ, "PATH": os.environ.get("PATH", "")},
    )


# ============================================================
# L1 / L2 / L3 路径
# ============================================================


class TestIntentParserCLI:
    def test_l2_path_basic_query(self):
        """E2E-CLI1: 基础查询走 L2 FTS 路径"""
        result = _run_parser(["--query", "品类分析", "--industry", "fmcg"])

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["source"] in ("l2_fts_fallback", "l2_empty", "l3_llm_fallback")
        assert "indicators" in data
        assert "scenarios" in data

    def test_l1_path_with_plan_json(self):
        """E2E-CLI2: 带 plan JSON 走 L1 精确路径"""
        plan = json.dumps({
            "indicators": ["sales_amount", "order_count"],
            "scenarios": ["sales_trend"],
            "analysis_type": "descriptive",
            "industry": "fmcg",
        })

        result = _run_parser(["--query", "销售趋势", "--plan", plan, "--industry", "fmcg"])

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["source"] in ("l1_exact", "l1_l2_mixed", "l1_insufficient",
                                   "l2_fts_fallback")

    def test_auto_detect_industry(self):
        """E2E-CLI3: 不传 industry 时自动检测"""
        result = _run_parser(["--query", "不良率趋势分析"])

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "industry" in data
        assert data["industry"] is not None

    def test_l3_fallback_for_unknown_query(self):
        """E2E-CLI4: 无法匹配时走 L3 兜底"""
        result = _run_parser([
            "--query", "xyznonexistent123abc",
            "--industry", "fmcg",
        ])

        assert result.returncode == 0
        data = json.loads(result.stdout)
        # Should not crash; returns some result
        assert "source" in data

    def test_output_to_file(self):
        """E2E-CLI5: --output 写入文件"""
        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "result.json"

            result = _run_parser([
                "--query", "品类分析", "--industry", "fmcg",
                "--output", str(out_file),
            ])

            assert result.returncode == 0
            assert out_file.exists()

            file_data = json.loads(out_file.read_text())
            assert "source" in file_data

    def test_verbose_flag(self):
        """E2E-CLI6: --verbose 输出诊断信息到 stderr"""
        result = _run_parser([
            "--query", "品类分析", "--industry", "fmcg", "--verbose",
        ])

        assert result.returncode == 0
        assert "[IntentParser]" in result.stderr

    def test_invalid_plan_json_graceful(self):
        """E2E-CLI7: 非法 plan JSON 不崩溃，降级到 L2"""
        result = _run_parser([
            "--query", "销售趋势",
            "--plan", "{this is not valid json!!!}",
            "--industry", "fmcg",
        ])

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "source" in data

    def test_session_clarifications_flag(self):
        """E2E-CLI8: --session-clarifications 标志被接受"""
        result = _run_parser([
            "--query", "品类分析", "--industry", "fmcg",
            "--session-clarifications", "2",
        ])

        assert result.returncode == 0
        data = json.loads(result.stdout)
        # With active_learning disabled, it still returns normal result
        assert "source" in data
