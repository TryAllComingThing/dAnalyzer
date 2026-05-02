# -*- coding: utf-8 -*-
"""
数据查询场景测试
通过自然语言触发 data-query 技能
"""

import pytest
from tests.cli.base import ClaudeCodeTester, PROJECT_ROOT


class TestDataQueryScenario:
    """数据查询场景测试"""

    @pytest.fixture
    def cli_tester(self):
        return ClaudeCodeTester(str(PROJECT_ROOT))

    def test_simple_query(self, cli_tester):
        """QUERY-001: 简单查询场景"""
        message = "查询最近7天的订单数据"

        response = cli_tester.send_message(message, timeout=60)

        # 检查 Claude 是否安装
        if not response["success"] and "not found" in response.get("stderr", ""):
            pytest.skip(f"Claude not installed: {response.get('stderr')}")

        # 验证响应
        assert len(response["response"]) > 0, "应该返回响应内容"

    def test_condition_query(self, cli_tester):
        """QUERY-002: 条件查询场景"""
        message = "查询上海地区销售额超过1000元的订单"

        response = cli_tester.send_message(message, timeout=60)

        if not response["success"] and "not found" in response.get("stderr", ""):
            pytest.skip(f"Claude not installed: {response.get('stderr')}")

        assert len(response["response"]) > 0

    def test_aggregation_query(self, cli_tester):
        """QUERY-003: 聚合统计场景"""
        message = "统计每个城市的订单数量"

        response = cli_tester.send_message(message, timeout=60)

        if not response["success"] and "not found" in response.get("stderr", ""):
            pytest.skip(f"Claude not installed: {response.get('stderr')}")

        assert len(response["response"]) > 0

    def test_time_range_query(self, cli_tester):
        """QUERY-004: 时间范围查询"""
        message = "查询2024年1月的销售数据"

        response = cli_tester.send_message(message, timeout=60)

        if not response["success"] and "not found" in response.get("stderr", ""):
            pytest.skip(f"Claude not installed: {response.get('stderr')}")

        assert len(response["response"]) > 0


class TestDataCleanScenario:
    """数据清洗场景测试"""

    @pytest.fixture
    def cli_tester(self):
        return ClaudeCodeTester(str(PROJECT_ROOT))

    def test_null_handling(self, cli_tester):
        """CLEAN-001: 空值处理场景"""
        message = "处理数据中的空值"

        response = cli_tester.send_message(message, timeout=60)

        if not response["success"] and "not found" in response.get("stderr", ""):
            pytest.skip(f"Claude not installed: {response.get('stderr')}")

        assert len(response["response"]) > 0

    def test_duplicate_removal(self, cli_tester):
        """CLEAN-002: 去重场景"""
        message = "去除重复订单"

        response = cli_tester.send_message(message, timeout=60)

        if not response["success"] and "not found" in response.get("stderr", ""):
            pytest.skip(f"Claude not installed: {response.get('stderr')}")

        assert len(response["response"]) > 0

    def test_abnormal_detection(self, cli_tester):
        """CLEAN-003: 异常值检测场景"""
        message = "检测并标记异常值"

        response = cli_tester.send_message(message, timeout=60)

        if not response["success"] and "not found" in response.get("stderr", ""):
            pytest.skip(f"Claude not installed: {response.get('stderr')}")

        assert len(response["response"]) > 0
