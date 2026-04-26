# -*- coding: utf-8 -*-
"""
data-quality-check 技能集成测试
测试用例: TC-QUALITY-001 ~ TC-QUALITY-004
"""

import pytest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestDataQualityCheck:
    """data-quality-check 技能测试"""

    def test_null_detection(self, sample_orders):
        """TC-QUALITY-001: 空值检测"""
        # 添加空值
        test_data = sample_orders.copy()
        test_data[0]["phone"] = None
        test_data[1]["email"] = ""
        test_data[0]["age"] = ""

        # 空值检测逻辑
        def detect_nulls(data):
            null_fields = {}
            for row in data:
                for field, value in row.items():
                    if value is None or value == "":
                        null_fields[field] = null_fields.get(field, 0) + 1
            return null_fields

        null_counts = detect_nulls(test_data)

        # 验证
        assert null_counts.get("phone", 0) >= 1
        assert null_counts.get("email", 0) >= 1

    def test_duplicate_detection(self, sample_orders):
        """TC-QUALITY-003: 重复检测"""
        # 添加重复数据
        test_data = sample_orders + [
            {"order_id": "O2024000001", "user_id": "U100001"},
            {"order_id": "O2024000002", "user_id": "U100002"},
        ]

        # 重复检测逻辑
        def detect_duplicates(data, key="order_id"):
            seen = {}
            duplicates = []
            for i, row in enumerate(data):
                val = row.get(key)
                if val in seen:
                    duplicates.append({"index": i, "value": val})
                else:
                    seen[val] = i
            return duplicates

        duplicates = detect_duplicates(test_data)

        # 验证
        assert len(duplicates) == 2

    def test_abnormal_detection_3sigma(self):
        """TC-QUALITY-002: 异常值检测 (3σ 原则)"""
        # 使用订单金额
        test_amounts = [100, 120, 110, 90, 130, 115, 125, 1000000]

        # 3σ 检测
        values = [float(x) for x in test_amounts]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = variance ** 0.5

        lower_bound = mean - 3 * std
        upper_bound = mean + 3 * std

        outliers = [x for x in values if x < lower_bound or x > upper_bound]

        # 验证 - 应该检测到 1000000
        assert len(outliers) > 0

    def test_continuity_detection(self):
        """TC-QUALITY-004: 连续性检测 (时间序列)"""
        # 时间序列数据
        test_dates = [
            "2024-01-01",
            "2024-01-02",
            "2024-01-03",
            "2024-01-05",  # 缺失 01-04
            "2024-01-06",
            "2024-01-08",  # 缺失 01-07
        ]

        from datetime import datetime, timedelta

        def detect_gaps(dates):
            sorted_dates = sorted(dates)
            gaps = []
            for i in range(len(sorted_dates) - 1):
                current = datetime.strptime(sorted_dates[i], "%Y-%m-%d")
                next_date = datetime.strptime(sorted_dates[i + 1], "%Y-%m-%d")
                if (next_date - current).days > 1:
                    gaps.append({
                        "from": sorted_dates[i],
                        "to": sorted_dates[i + 1],
                        "missing_days": (next_date - current).days - 1
                    })
            return gaps

        gaps = detect_gaps(test_dates)

        # 验证
        assert len(gaps) == 2
        assert any(g["missing_days"] == 1 for g in gaps)


class TestDataQualityWithRealData:
    """使用真实数据进行质量检测"""

    def test_quality_check_on_orders(self, orders_csv_data):
        """对 test_orders.csv 进行质量检测"""
        if not orders_csv_data:
            pytest.skip("No data available")

        # 检测空值
        null_counts = {}
        for row in orders_csv_data:
            for field, value in row.items():
                if not value or value.strip() == "":
                    null_counts[field] = null_counts.get(field, 0) + 1

        print(f"\n空值统计: {null_counts}")

        # 检测重复 order_id
        order_ids = [row.get("order_id") for row in orders_csv_data]
        unique_ids = set(order_ids)
        duplicate_count = len(order_ids) - len(unique_ids)

        print(f"订单总数: {len(order_ids)}")
        print(f"唯一订单数: {len(unique_ids)}")
        print(f"重复订单数: {duplicate_count}")

        # 验证
        assert len(order_ids) > 0
        assert duplicate_count == 0, "测试数据不应有重复"

    def test_quality_check_on_users(self, users_csv_data):
        """对 test_users.csv 进行质量检测"""
        if not users_csv_data:
            pytest.skip("No data available")

        # 检测空值
        null_counts = {}
        for row in users_csv_data:
            for field, value in row.items():
                if not value or value.strip() == "":
                    null_counts[field] = null_counts.get(field, 0) + 1

        print(f"\n用户数据空值统计: {null_counts}")

        # 检测异常年龄
        abnormal_ages = []
        for row in users_csv_data:
            try:
                age = int(row.get("age", 0))
                if age < 0 or age > 150:
                    abnormal_ages.append({"user_id": row.get("user_id"), "age": age})
            except (ValueError, TypeError):
                abnormal_ages.append({"user_id": row.get("user_id"), "age": row.get("age")})

        print(f"异常年龄数: {len(abnormal_ages)}")


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
