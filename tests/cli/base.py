# -*- coding: utf-8 -*-
"""
Claude Code CLI 测试基类
通过 subprocess 调用 claude 命令进行测试
"""

import subprocess
import os
import pytest
from pathlib import Path
from typing import Dict, Optional


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent.parent


PROJECT_ROOT = get_project_root()
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")


class ClaudeCodeTester:
    """Claude Code CLI 测试工具"""

    def __init__(self, project_path: Optional[str] = None):
        self.project_path = Path(project_path) if project_path else PROJECT_ROOT
        self.test_data_dir = self.project_path / "tests" / "data" / "sample"

    def run_command(self, command: str, timeout: int = 60) -> Dict:
        """
        运行 Claude Code 命令并返回结果

        Args:
            command: 要执行的命令（不含 claude 前缀）
            timeout: 超时时间（秒）

        Returns:
            {"stdout": "...", "stderr": "...", "returncode": 0}
        """
        cmd = [CLAUDE_BIN, command]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=timeout,
                input=""
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timeout after {timeout}s",
                "returncode": -1
            }
        except FileNotFoundError:
            return {
                "stdout": "",
                "stderr": f"Claude binary not found: {CLAUDE_BIN}",
                "returncode": -1
            }

    def send_message(self, message: str, timeout: int = 120) -> Dict:
        """
        发送消息给 Claude Code

        Args:
            message: 用户消息
            timeout: 超时时间

        Returns:
            {"response": "...", "success": bool, "stderr": "..."}
        """
        # 使用 --print 选项获取纯输出
        cmd = [CLAUDE_BIN, "--print", "-p", message]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                "response": result.stdout,
                "success": result.returncode == 0,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "response": "",
                "success": False,
                "stderr": f"Message timeout after {timeout}s"
            }
        except FileNotFoundError:
            return {
                "response": "",
                "success": False,
                "stderr": f"Claude binary not found: {CLAUDE_BIN}"
            }

    def send_message_stream(self, message: str, timeout: int = 120) -> str:
        """
        流式发送消息

        Args:
            message: 用户消息
            timeout: 超时时间

        Returns:
            完整响应文本
        """
        cmd = [CLAUDE_BIN, "-p", message]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            return f"Timeout after {timeout}s"
        except FileNotFoundError:
            return f"Claude binary not found: {CLAUDE_BIN}"

    def check_skill_available(self, skill_name: str) -> bool:
        """检查技能是否可用"""
        result = self.run_command("/help", timeout=30)

        if result["returncode"] != 0:
            return False

        return skill_name.lower() in result["stdout"].lower()

    def get_test_data_path(self, filename: str) -> Path:
        """获取测试数据路径"""
        return self.test_data_dir / filename


@pytest.fixture
def cli_tester():
    """CLI 测试 fixture"""
    return ClaudeCodeTester(str(PROJECT_ROOT))


@pytest.fixture
def cli_tester_with_data():
    """带测试数据的 CLI 测试 fixture"""
    tester = ClaudeCodeTester(str(PROJECT_ROOT))

    # 验证测试数据存在
    data_file = tester.get_test_data_path("test_orders.csv")
    if not data_file.exists():
        pytest.skip(f"Test data not found: {data_file}")

    return tester
