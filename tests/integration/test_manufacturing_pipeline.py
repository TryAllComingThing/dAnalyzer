# -*- coding: utf-8 -*-
"""
制造行业管道集成测试

验证制造行业（生产质量分析场景）全链路:
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

TEST_CSV = str(PROJECT_ROOT / "tests" / "data" / "sample" / "test_manufacturing_production.csv")
TEST_QUERY = "生产效率"


class TestManufacturingPipeline:
    """制造数据管道全链路测试"""

    def test_manufacturing_pipeline_full_flow(self):
        """TC-MFG-001: 全链路运行验证"""
        result = run_pipeline(TEST_QUERY, TEST_CSV, industry="manufacturing")

        assert result["pipeline"] == "manufacturing"
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

    def test_manufacturing_pipeline_analysis_yield(self):
        """TC-MFG-002: 良品率分析结果正确"""
        result = run_pipeline(TEST_QUERY, TEST_CSV, industry="manufacturing")

        analysis = result["steps"]["analysis"]
        assert analysis["total_orders"] > 0
        assert analysis["total_planned"] > 0
        assert analysis["total_actual"] > 0
        assert analysis["total_defect"] > 0
        assert analysis["yield_rate_pct"] > 0
        assert analysis["capacity_utilization_pct"] > 0

    def test_manufacturing_step1_context_retrieval(self):
        """TC-MFG-003: 上下文检索 — 返回制造相关指标"""
        context = step1_retrieve_context(TEST_QUERY, "manufacturing")

        assert "indicators" in context
        assert len(context["indicators"]) > 0

        indicator_codes = {i.get("code") for i in context["indicators"]}
        assert "capacity_utilization" in indicator_codes, "缺少产能利用率指标"

    def test_manufacturing_step3_analysis_schema(self):
        """TC-MFG-004: 制造分析输出 schema 验证"""
        rows = step2_load_data(TEST_CSV)
        result = step3_analyze(rows, TEST_QUERY, industry="manufacturing")

        assert result["total_orders"] == len(rows)
        assert result["total_actual"] > 0
        assert result["total_planned"] > 0

        # 产能利用率 0-100%
        assert 0 <= result["capacity_utilization_pct"] <= 100
        # 良品率 0-100%
        assert 0 <= result["yield_rate_pct"] <= 100
        # 不良品率 0-100%
        assert 0 <= result["defect_rate_pct"] <= 100

        assert result["analysis_time_ms"] >= 0

    def test_manufacturing_pipeline_security(self):
        """TC-MFG-005: 聚合制造数据安全级别应为 LOW"""
        result = run_pipeline(TEST_QUERY, TEST_CSV, industry="manufacturing")
        assert result["steps"]["security"]["pass"] is True
        assert result["steps"]["security"]["level"] == "LOW"

    def test_manufacturing_pipeline_single_record(self):
        """TC-MFG-006: 单行工单数据处理"""
        rows = step2_load_data(TEST_CSV)
        single_row = [rows[0]]
        result = step3_analyze(single_row, TEST_QUERY, industry="manufacturing")

        assert result["total_orders"] == 1
        assert result["total_actual"] > 0
        assert result["defect_rate_pct"] >= 0

    def test_manufacturing_pipeline_no_defects(self):
        """TC-MFG-007: 无不良品时的处理"""
        rows = step2_load_data(TEST_CSV)
        for r in rows:
            r["defect_qty"] = "0"
            r["rework_qty"] = "0"
        result = step3_analyze(rows[:3], TEST_QUERY, industry="manufacturing")

        assert result["total_defect"] == 0
        assert result["defect_rate_pct"] == 0
        assert result["yield_rate_pct"] == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
