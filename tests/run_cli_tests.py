# -*- coding: utf-8 -*-
"""
dAnalyzer CLI 测试运行脚本

使用方式:
    python tests/run_cli_tests.py           # 运行所有测试
    python tests/run_cli_tests.py cli        # 仅 CLI 测试
    python tests/run_cli_tests.py scenario   # 仅场景测试
    python tests/run_cli_tests.py e2e        # 仅 E2E 测试
"""

import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_tests(test_path: str = "tests", markers: str = ""):
    """运行测试"""
    cmd = [sys.executable, "-m", "pytest", test_path, "-v"]

    if markers:
        cmd.extend(["-m", markers])

    # 设置环境变量
    env = os.environ.copy()
    env["CLAUDE_BIN"] = env.get("CLAUDE_BIN", "claude")

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    return result.returncode


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "cli":
            print("=" * 60)
            print("运行 CLI 测试")
            print("=" * 60)
            return run_tests("tests/cli")

        elif arg == "scenario":
            print("=" * 60)
            print("运行场景测试")
            print("=" * 60)
            return run_tests("tests/scenario")

        elif arg == "e2e":
            print("=" * 60)
            print("运行 E2E 测试")
            print("=" * 60)
            return run_tests("tests/e2e")

        elif arg == "unit":
            print("=" * 60)
            print("运行单元测试")
            print("=" * 60)
            return run_tests("tests/unit")

        elif arg == "integration":
            print("=" * 60)
            print("运行集成测试")
            print("=" * 60)
            return run_tests("tests/integration")

    # 默认运行所有测试
    print("=" * 60)
    print("dAnalyzer CLI 测试")
    print("=" * 60)
    return run_tests("tests")


if __name__ == "__main__":
    sys.exit(main())
