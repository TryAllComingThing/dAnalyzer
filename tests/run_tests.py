# -*- coding: utf-8 -*-
"""
测试运行脚本
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("dAnalyzer 测试执行")
    print("=" * 60)

    # 运行 pytest
    cmd = [
        sys.executable, "-m", "pytest",
        str(PROJECT_ROOT / "tests"),
        "-v",           # 详细输出
        "--tb=short",  # 简短的 traceback
        "-x",          # 第一个失败后停止
    ]

    result = subprocess.run(cmd)
    return result.returncode


def run_unit_tests():
    """仅运行单元测试"""
    print("=" * 60)
    print("单元测试")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "pytest",
        str(PROJECT_ROOT / "tests" / "unit"),
        "-v",
    ]

    result = subprocess.run(cmd)
    return result.returncode


def run_integration_tests():
    """仅运行集成测试"""
    print("=" * 60)
    print("集成测试")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "pytest",
        str(PROJECT_ROOT / "tests" / "integration"),
        "-v",
    ]

    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "unit":
            sys.exit(run_unit_tests())
        elif cmd == "integration":
            sys.exit(run_integration_tests())

    sys.exit(run_tests())
