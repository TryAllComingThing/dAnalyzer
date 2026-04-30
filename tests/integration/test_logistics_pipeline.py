# -*- coding: utf-8 -*-
"""
物流行业管道集成测试

验证物流行业（配送效率分析场景）全链路:
  用户查询 → 上下文检索 → 数据加载 → 分析 → 安全扫描
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ecommerce_pipeline import (
    run_pipeline,
    step1_retrieve_context,
    step2_load_data,
    step3_analyze,
)

TEST_CSV = str(PROJECT_ROOT / "tests" / "data" / "sample" / "test_logistics_waybills.csv")
TEST_QUERY = "配送效率"


class TestLogisticsPipeline:
    """物流数据管道全链路测试"""

    def test_logistics_pipeline_full_flow(self):
        """TC-LOG-001: 全链路运行验证"""
        result = run_pipeline(TEST_QUERY, TEST_CSV, industry="logistics")

        assert result["pipeline"] == "logistics"
        assert result["query"] == TEST_QUERY

        steps = result["steps"]
        assert "context_retrieval" in steps
        assert "data_loading" in steps
        assert "analysis" in steps
        assert "security" in steps

        assert result["timing"]["total_ms"] > 0

        summary = result["summary"]
        assert summary["total_indicators"] > 0
        assert summary["total_rows_loaded"] > 0

    def test_logistics_pipeline_analysis_delivery(self):
        """TC-LOG-002: 配送效率分析结果正确"""
        result = run_pipeline(TEST_QUERY, TEST_CSV, industry="logistics")

        analysis = result["steps"]["analysis"]
        assert analysis["total_waybills"] > 0
        assert analysis["delivered"] > 0
        assert analysis["delivery_rate"] > 0
        assert analysis["avg_delivery_hours"] > 0

        # 有运输中的记录
        assert analysis.get("in_transit", 0) >= 0

    def test_logistics_step1_context_retrieval(self):
        """TC-LOG-003: 上下文检索 — 返回物流相关指标"""
        context = step1_retrieve_context(TEST_QUERY, "logistics")

        assert "indicators" in context
        assert len(context["indicators"]) > 0

        indicator_codes = {i.get("code") for i in context["indicators"]}
        assert "delivery_time" in indicator_codes, "缺少配送时效指标"

    def test_logistics_step3_analysis_schema(self):
        """TC-LOG-004: 物流分析输出 schema 验证"""
        rows = step2_load_data(TEST_CSV)
        result = step3_analyze(rows, TEST_QUERY, industry="logistics")

        assert result["total_waybills"] == len(rows)
        assert result["total_weight_kg"] > 0
        assert result["delivery_rate"] > 0
        assert result["avg_delivery_hours"] > 0

        # 妥投率应在 0-100% 之间
        assert 0 <= result["delivery_rate"] <= 100

    def test_logistics_pipeline_security(self):
        """TC-LOG-005: 聚合物流数据安全级别应为 LOW"""
        result = run_pipeline(TEST_QUERY, TEST_CSV, industry="logistics")
        assert result["steps"]["security"]["pass"] is True
        assert result["steps"]["security"]["level"] == "LOW"

    def test_logistics_pipeline_single_record(self):
        """TC-LOG-006: 单行运单数据处理"""
        rows = step2_load_data(TEST_CSV)
        single_row = [rows[0]]
        result = step3_analyze(single_row, TEST_QUERY, industry="logistics")

        assert result["total_waybills"] == 1
        assert result["delivered"] <= 1

    def test_logistics_pipeline_all_in_transit(self):
        """TC-LOG-007: 全在途运单处理（无签收时间）"""
        rows = step2_load_data(TEST_CSV)
        # 模拟所有运单在途
        for r in rows:
            r["sign_time"] = ""
            r["status"] = "运输中"
        result = step3_analyze(rows[:5], TEST_QUERY, industry="logistics")
        assert result["total_waybills"] == 5
        assert result["delivered"] == 0
        assert result["in_transit"] == 5
        assert result["avg_delivery_hours"] == 0  # 无签收数据


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
