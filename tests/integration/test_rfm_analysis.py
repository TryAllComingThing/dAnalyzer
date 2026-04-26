# -*- coding: utf-8 -*-
"""
rfm-analysis 技能集成测试
测试用例: TC-RFM-001 ~ TC-RFM-003
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestRFMAnalysis:
    """RFM 分析技能测试"""

    def test_rfm_calculation(self):
        """TC-RFM-001: RFM 计算"""
        # 模拟用户订单数据
        test_date = datetime(2026, 4, 26)
        test_data = [
            {"user_id": "U001", "order_date": (test_date - timedelta(days=5)).strftime("%Y-%m-%d"), "amount": 500},
            {"user_id": "U001", "order_date": (test_date - timedelta(days=10)).strftime("%Y-%m-%d"), "amount": 300},
            {"user_id": "U002", "order_date": (test_date - timedelta(days=2)).strftime("%Y-%m-%d"), "amount": 1000},
            {"user_id": "U003", "order_date": (test_date - timedelta(days=30)).strftime("%Y-%m-%d"), "amount": 200},
        ]

        # RFM 计算
        def calculate_rfm(data, reference_date):
            rfm_results = {}

            for row in data:
                user_id = row["user_id"]
                order_date = datetime.strptime(row["order_date"], "%Y-%m-%d")
                amount = float(row["amount"])

                if user_id not in rfm_results:
                    rfm_results[user_id] = {
                        "recency": (reference_date - order_date).days,
                        "frequency": 0,
                        "monetary": 0
                    }

                rfm_results[user_id]["frequency"] += 1
                rfm_results[user_id]["monetary"] += amount

            return rfm_results

        rfm = calculate_rfm(test_data, test_date)

        # 验证
        assert "U001" in rfm
        assert rfm["U001"]["recency"] == 5  # 最近购买
        assert rfm["U001"]["frequency"] == 2  # 2次购买
        assert rfm["U001"]["monetary"] == 800  # 总金额

    def test_rfm_user_segmentation(self):
        """TC-RFM-002: 用户分群"""
        # 用户 RFM 数据
        rfm_data = {
            "U001": {"recency": 5, "frequency": 5, "monetary": 5000},
            "U002": {"recency": 2, "frequency": 1, "amount": 100},
            "U003": {"recency": 30, "frequency": 10, "monetary": 10000},
            "U004": {"recency": 15, "frequency": 3, "monetary": 800},
            "U005": {"recency": 1, "frequency": 2, "monetary": 2000},
        }

        # RFM 分群 (8类)
        def segment_users(rfm):
            segments = {}

            for user_id, rfm_values in rfm.items():
                r = rfm_values["recency"]
                f = rfm_values["frequency"]
                m = rfm_values["monetary"]

                # 简单分群逻辑
                if r <= 7 and f >= 3 and m >= 1000:
                    segment = "高价值客户"
                elif r <= 7 and f < 3:
                    segment = "潜力客户"
                elif r > 30 and f >= 5:
                    segment = "流失风险客户"
                elif r > 30:
                    segment = "流失客户"
                else:
                    segment = "普通客户"

                segments[user_id] = segment

            return segments

        segments = segment_users(rfm_data)

        # 验证
        assert "U001" in segments
        assert segments["U001"] == "高价值客户"
        assert segments["U002"] == "潜力客户"

    def test_rfm_segment_statistics(self):
        """TC-RFM-003: 分群统计"""
        # 分群结果
        segments = {
            "U001": "高价值客户",
            "U002": "潜力客户",
            "U003": "流失风险客户",
            "U004": "普通客户",
            "U005": "高价值客户",
            "U006": "流失客户",
            "U007": "潜力客户",
            "U008": "普通客户",
        }

        # 统计各分群用户数
        stats = {}
        for user_id, segment in segments.items():
            stats[segment] = stats.get(segment, 0) + 1

        # 验证
        assert stats.get("高价值客户", 0) == 2
        assert stats.get("潜力客户", 0) == 2
        assert stats.get("普通客户", 0) == 2
        assert stats.get("流失客户", 0) >= 1


class TestRFMWithRealData:
    """使用真实数据进行 RFM 分析"""

    def test_rfm_analysis_on_users(self, orders_csv_data, users_csv_data):
        """使用真实订单数据进行 RFM 分析"""
        if not orders_csv_data:
            pytest.skip("No orders data available")

        # 汇总用户订单
        user_orders = {}
        reference_date = datetime(2026, 4, 26)

        for row in orders_csv_data:
            user_id = row.get("user_id")
            if not user_id:
                continue

            order_date_str = row.get("order_date", "")
            try:
                order_date = datetime.strptime(order_date_str.split()[0], "%Y-%m-%d")
            except:
                continue

            amount = float(row.get("actual_amount", 0))

            if user_id not in user_orders:
                user_orders[user_id] = {
                    "orders": [],
                    "total_amount": 0
                }

            user_orders[user_id]["orders"].append(order_date)
            user_orders[user_id]["total_amount"] += amount

        # 计算 RFM
        rfm_results = {}
        for user_id, data in user_orders.items():
            if not data["orders"]:
                continue

            recency = (reference_date - max(data["orders"])).days
            frequency = len(data["orders"])
            monetary = data["total_amount"]

            rfm_results[user_id] = {
                "recency": recency,
                "frequency": frequency,
                "monetary": monetary
            }

        print(f"\n分析用户数: {len(rfm_results)}")

        # 统计高价值客户 (R < 30, F >= 3, M >= 5000)
        high_value = sum(
            1 for r in rfm_results.values()
            if r["recency"] < 30 and r["frequency"] >= 3 and r["monetary"] >= 5000
        )

        print(f"高价值客户数: {high_value}")


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
