"""RFM 分群单元测试

测试 scripts/rfm_segmentation.py 的 calculate_rfm 和 segment_users 函数。
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.rfm_segmentation import calculate_rfm, segment_users


REF_DATE = datetime(2026, 5, 1)


def _d(days_ago: int) -> str:
    """Helper: 返回 days_ago 天前的日期字符串"""
    return (REF_DATE - timedelta(days=days_ago)).strftime("%Y-%m-%d")


class TestCalculateRFM:
    def test_basic_calculation(self):
        orders = [
            {"user_id": "U1", "order_date": _d(5), "amount": 500},
            {"user_id": "U1", "order_date": _d(10), "amount": 300},
            {"user_id": "U2", "order_date": _d(2), "amount": 1000},
        ]
        rfm = calculate_rfm(orders, REF_DATE)
        assert rfm["U1"]["recency"] == 5
        assert rfm["U1"]["frequency"] == 2
        assert rfm["U1"]["monetary"] == 800.0
        assert rfm["U2"]["recency"] == 2
        assert rfm["U2"]["frequency"] == 1
        assert rfm["U2"]["monetary"] == 1000.0

    def test_single_order(self):
        orders = [{"user_id": "U1", "order_date": _d(3), "amount": 200}]
        rfm = calculate_rfm(orders, REF_DATE)
        assert rfm["U1"]["recency"] == 3
        assert rfm["U1"]["frequency"] == 1
        assert rfm["U1"]["monetary"] == 200.0

    def test_recency_zero(self):
        orders = [{"user_id": "U1", "order_date": REF_DATE.strftime("%Y-%m-%d"), "amount": 100}]
        rfm = calculate_rfm(orders, REF_DATE)
        assert rfm["U1"]["recency"] == 0

    def test_empty_input(self):
        assert calculate_rfm([], REF_DATE) == {}

    def test_invalid_date_skipped(self):
        orders = [
            {"user_id": "U1", "order_date": "not-a-date", "amount": 100},
            {"user_id": "U1", "order_date": _d(3), "amount": 200},
        ]
        rfm = calculate_rfm(orders, REF_DATE)
        assert rfm["U1"]["frequency"] == 1  # invalid row skipped

    def test_negative_amount(self):
        orders = [{"user_id": "U1", "order_date": _d(5), "amount": -50}]
        rfm = calculate_rfm(orders, REF_DATE)
        assert rfm["U1"]["monetary"] == -50.0

    def test_missing_amount_defaults_zero(self):
        orders = [{"user_id": "U1", "order_date": _d(1)}]
        rfm = calculate_rfm(orders, REF_DATE)
        assert rfm["U1"]["monetary"] == 0.0


class TestSegmentUsers:
    def test_high_value(self):
        rfm = {"U1": {"recency": 5, "frequency": 5, "monetary": 5000}}
        assert segment_users(rfm)["U1"] == "高价值客户"

    def test_potential(self):
        rfm = {"U1": {"recency": 5, "frequency": 1, "monetary": 100}}
        assert segment_users(rfm)["U1"] == "潜力客户"

    def test_churn_risk(self):
        rfm = {"U1": {"recency": 60, "frequency": 10, "monetary": 20000}}
        assert segment_users(rfm)["U1"] == "流失风险客户"

    def test_churned(self):
        rfm = {"U1": {"recency": 60, "frequency": 2, "monetary": 100}}
        assert segment_users(rfm)["U1"] == "流失客户"

    def test_normal(self):
        rfm = {"U1": {"recency": 15, "frequency": 2, "monetary": 500}}
        assert segment_users(rfm)["U1"] == "普通客户"

    def test_empty_input(self):
        assert segment_users({}) == {}

    def test_boundary_recency_7(self):
        """R=7 仍在高价值/潜力范围内"""
        rfm = {"U1": {"recency": 7, "frequency": 3, "monetary": 1000}}
        assert segment_users(rfm)["U1"] == "高价值客户"

    def test_boundary_recency_8(self):
        """R=8 落入普通客户"""
        rfm = {"U1": {"recency": 8, "frequency": 3, "monetary": 1000}}
        assert segment_users(rfm)["U1"] == "普通客户"
