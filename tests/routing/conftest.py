"""
路由测试公共配置 — Claude CLI 可用性检查 + 优先级标记
"""

import os
import subprocess
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")


def claude_available() -> bool:
    """检查 Claude Code CLI 是否可用"""
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def pytest_configure(config):
    """注册自定义 markers + 检查 CLI 可用性"""
    config.addinivalue_line("markers", "p0: 核心路径 — 每次提交运行")
    config.addinivalue_line("markers", "p1: 重要路径 — 每日运行")
    config.addinivalue_line("markers", "p2: 覆盖路径 — 发版前运行")
    config.addinivalue_line("markers", "p3: 深度路径 — 专项测试")

    if not claude_available():
        config.option.routing_skip = True
    else:
        config.option.routing_skip = False


def pytest_collection_modifyitems(config, items):
    """自动标记优先级 + 不可用时跳过"""
    for item in items:
        # 按类名自动分配 p0/p1/p2/p3 标记
        cls = item.parent if item.parent else None
        cls_name = getattr(cls, 'name', '') if cls else ''
        if cls_name:
            for prio in ("P0", "P1", "P2", "P3"):
                if prio in cls_name:
                    item.add_marker(getattr(pytest.mark, prio.lower()))
                    break

    # Claude 不可用时跳过所有路由测试
    if getattr(config.option, "routing_skip", False):
        skip_msg = f"Claude Code CLI ({CLAUDE_BIN}) 不可用，跳过路由测试"
        for item in items:
            item.add_marker(pytest.mark.skip(reason=skip_msg))
