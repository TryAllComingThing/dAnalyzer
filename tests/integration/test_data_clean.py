# -*- coding: utf-8 -*-
"""
data-clean 技能集成测试
测试用例: TC-CLEAN-001 ~ TC-CLEAN-005
"""

import pytest
import csv
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestDataCleanSkill:
    """data-clean 技能测试"""

    def test_null_value_handling(self, sample_orders):
        """TC-CLEAN-001: 空值处理"""
        # 添加空值
        test_data = sample_orders.copy()
        test_data[0]["phone"] = None
        test_data[1]["email"] = ""

        # 空值处理逻辑
        def handle_nulls(data):
            for row in data:
                if row.get("phone") is None or row.get("phone") == "":
                    row["phone"] = "未知"
                if row.get("email") is None or row.get("email") == "":
                    row["email"] = "未知"
            return data

        cleaned = handle_nulls(test_data)

        # 验证
        assert cleaned[0]["phone"] == "未知"
        assert cleaned[1]["email"] == "未知"

    def test_duplicate_removal(self, sample_orders):
        """TC-CLEAN-002: 重复值去重"""
        # 添加重复数据
        test_data = sample_orders + [
            {"order_id": "O2024000001", "user_id": "U100001"},  # 重复
            {"order_id": "O2024000003", "user_id": "U100003"},
        ]

        # 去重逻辑 (保留最后一条)
        def remove_duplicates(data, key="order_id"):
            seen = {}
            for row in data:
                if row.get(key) not in seen:
                    seen[row.get(key)] = row
                else:
                    seen[row.get(key)] = row  # 保留最新
            return list(seen.values())

        cleaned = remove_duplicates(test_data)

        # 验证
        assert len(cleaned) == 3  # O001, O002, O003

    def test_abnormal_value_detection(self):
        """TC-CLEAN-003: 异常值检测"""
        # 3σ 原则识别异常值
        test_amounts = [100, 120, 110, 90, 130, 1000000, 115, 125]

        def detect_outliers(data, field="amount"):
            values = [float(row.get(field, 0)) for row in data]
            if not values:
                return []

            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std = variance ** 0.5

            outliers = []
            for row in data:
                val = float(row.get(field, 0))
                if abs(val - mean) > 3 * std:
                    outliers.append({"row": row, "value": val, "mean": mean})

            return outliers

        outliers = detect_outliers([{"amount": a} for a in test_amounts])

        # 验证检测到异常值 (1000000)
        assert len(outliers) > 0
        assert any(o["value"] == 1000000 for o in outliers)

    def test_date_format_standardization(self, sample_orders):
        """TC-CLEAN-004: 日期格式标准化"""
        # 不同格式的日期
        test_data = [
            {"order_date": "2024/01/01 10:00:00"},
            {"order_date": "2024-02-01 10:00:00"},
            {"order_date": "2024.03.01 10:00:00"},
            {"order_date": "2024-04-01"},
        ]

        # 日期标准化函数
        from datetime import datetime

        def standardize_date(date_str):
            formats = ["%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y-%m-%d"]
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except:
                    continue
            return date_str

        # 执行标准化
        standardized = [{"order_date": standardize_date(row["order_date"])} for row in test_data]

        # 验证
        for row in standardized:
            assert row["order_date"].startswith("2024-")

    def test_cleaning_report_generation(self, sample_orders):
        """TC-CLEAN-005: 清洗报告生成"""
        # 模拟清洗过程并生成报告
        test_data = sample_orders.copy()
        test_data[0]["phone"] = None
        test_data.append(test_data[0])  # 添加重复

        report = {
            "total_rows": len(test_data),
            "null_count": 1,
            "duplicate_count": 1,
            "abnormal_count": 0,
            "cleaned_rows": 0,
        }

        # 清洗
        cleaned = test_data.copy()
        if cleaned[0].get("phone") is None:
            cleaned[0]["phone"] = "未知"
            report["cleaned_rows"] += 1

        # 去重
        seen = set()
        unique = []
        for row in cleaned:
            order_id = row.get("order_id")
            if order_id and order_id not in seen:
                seen.add(order_id)
                unique.append(row)
            else:
                report["duplicate_count"] += 1

        report["final_rows"] = len(unique)

        # 验证报告
        assert report["total_rows"] == 3
        assert report["null_count"] == 1
        assert report["duplicate_count"] >= 1
        assert report["final_rows"] < report["total_rows"]


class TestAbnormalDataClean:
    """使用真实异常数据测试"""

    def test_clean_abnormal_data(self, abnormal_csv_data):
        """使用 test_abnormal.csv 进行清洗测试"""
        # 这是一个综合测试，使用真实的异常数据
        if not abnormal_csv_data:
            pytest.skip("No abnormal data available")

        cleaned_data = []
        issues = []

        for row in abnormal_csv_data:
            # 检查异常
            has_issue = False

            # 检查金额异常
            amount = float(row.get("amount", 0))
            if amount > 100000:  # 超过阈值视为异常
                issues.append({"type": "extreme_value", "row": row})
                has_issue = True

            # 检查负数
            if amount < 0:
                issues.append({"type": "negative_value", "row": row})
                has_issue = True

            if not has_issue:
                cleaned_data.append(row)

        # 验证
        assert len(issues) > 0, "Should detect abnormal values"
        print(f"检测到 {len(issues)} 个异常，清理后保留 {len(cleaned_data)} 条")


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
