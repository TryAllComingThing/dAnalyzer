# -*- coding: utf-8 -*-
"""
RFM分析场景测试
"""

import pytest
from tests.cli.base import ClaudeCodeTester, PROJECT_ROOT


class TestRFMAnalysisScenario:
    """RFM分析场景测试"""

    @pytest.fixture
    def cli_tester(self):
        return ClaudeCodeTester(str(PROJECT_ROOT))

    def test_rfm_calculation(self, cli_tester):
        """RFM-001: RFM计算"""
        message = "对我的用户数据进行RFM分析"

        response = cli_tester.send_message(message, timeout=120)

        if not response["success"] and "not found" in response.get("stderr", ""):
            pytest.skip(f"Claude not installed: {response.get('stderr')}")

        assert len(response["response"]) > 0

    def test_user_segmentation(self, cli_tester):
        """RFM-002: 用户分群"""
        message = "将用户按RFM得分划分为不同群体"

        response = cli_tester.send_message(message, timeout=120)

        if not response["success"] and "not found" in response.get("stderr", ""):
            pytest.skip(f"Claude not installed: {response.get('stderr')}")

        assert len(response["response"]) > 0
