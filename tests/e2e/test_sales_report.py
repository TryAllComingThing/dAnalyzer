# -*- coding: utf-8 -*-
"""
端到端测试
验证完整的数据分析流程
"""

import pytest
from tests.cli.base import ClaudeCodeTester, PROJECT_ROOT


class TestSalesReportE2E:
    """销售周报 E2E 测试"""

    @pytest.fixture
    def cli_tester(self):
        return ClaudeCodeTester(str(PROJECT_ROOT))

    def test_step_by_step_flow(self, cli_tester):
        """E2E-001: 逐步执行分析流程"""
        # 步骤1: 查询数据
        message = "查询2024年1月的订单数据"
        response = cli_tester.send_message(message, timeout=120)

        if not response["success"] and "not found" in response.get("stderr", ""):
            pytest.skip(f"Claude not installed: {response.get('stderr')}")

        # 验证第一步完成
        assert len(response["response"]) > 0

    def test_single_request_flow(self, cli_tester):
        """E2E-002: 单次请求完成分析"""
        message = "帮我分析销售数据，统计各类目销售额"

        response = cli_tester.send_message(message, timeout=180)

        if not response["success"] and "not found" in response.get("stderr", ""):
            pytest.skip(f"Claude not installed: {response.get('stderr')}")

        # 验证返回了分析结果
        assert len(response["response"]) > 100, "应该返回完整的分析结果"

    def test_rfm_complete_flow(self, cli_tester):
        """E2E-003: RFM 完整流程"""
        message = "请对我的用户进行RFM分析，并划分用户群体"

        response = cli_tester.send_message(message, timeout=180)

        if not response["success"] and "not found" in response.get("stderr", ""):
            pytest.skip(f"Claude not installed: {response.get('stderr')}")

        assert len(response["response"]) > 0
