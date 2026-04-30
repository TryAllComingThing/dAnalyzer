# -*- coding: utf-8 -*-
"""
金融行业管道集成测试

验证金融行业（不良率分析场景）全链路:
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

TEST_CSV = str(PROJECT_ROOT / "tests" / "data" / "sample" / "test_finance_loans.csv")
TEST_QUERY = "不良贷款率"


class TestFinancePipeline:
    """金融数据管道全链路测试"""

    def test_finance_pipeline_full_flow(self):
        """TC-FIN-001: 全链路运行验证"""
        result = run_pipeline(TEST_QUERY, TEST_CSV, industry="finance")

        assert result["pipeline"] == "finance"
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

    def test_finance_pipeline_analysis_npl(self):
        """TC-FIN-002: 不良贷款率计算正确"""
        result = run_pipeline(TEST_QUERY, TEST_CSV, industry="finance")

        analysis = result["steps"]["analysis"]
        assert analysis["npl_ratio"] > 0
        assert analysis["total_balance"] > 0
        assert analysis["total_loans"] > 0
        assert "classification_distribution" in analysis

        # 五级分类应包含正常/关注/次级/可疑/损失
        dist = analysis["classification_distribution"]
        assert "正常" in dist
        assert "次级" in dist

    def test_finance_step1_context_retrieval(self):
        """TC-FIN-003: 上下文检索 — 返回金融相关指标"""
        context = step1_retrieve_context(TEST_QUERY, "finance")

        assert "indicators" in context
        assert len(context["indicators"]) > 0

        indicator_codes = {i.get("code") for i in context["indicators"]}
        assert "npl_ratio" in indicator_codes, "缺少不良贷款率指标"

    def test_finance_step3_analysis_schema(self):
        """TC-FIN-004: 金融分析输出 schema 验证"""
        rows = step2_load_data(TEST_CSV)
        result = step3_analyze(rows, TEST_QUERY, industry="finance")

        assert result["total_loans"] == len(rows)
        assert result["total_balance"] > 0
        assert result["total_loan_amount"] > 0
        assert result["npl_ratio"] >= 0
        assert result["npl_balance"] > 0  # 有不良贷款数据

        # 不良贷款率应在合理范围 0-100%
        assert 0 <= result["npl_ratio"] <= 100
        assert result["analysis_time_ms"] >= 0

    def test_finance_pipeline_security(self):
        """TC-FIN-005: 聚合金融数据安全级别应为 LOW"""
        result = run_pipeline(TEST_QUERY, TEST_CSV, industry="finance")
        assert result["steps"]["security"]["pass"] is True
        assert result["steps"]["security"]["level"] == "LOW"

    def test_finance_pipeline_edge_empty_classification(self):
        """TC-FIN-006: 贷款分类为空时的处理"""
        rows = step2_load_data(TEST_CSV)
        # 模拟没有分类的数据
        empty_rows = [{k: ("" if k == "classification" else v) for k, v in rows[0].items()}]
        result = step3_analyze(empty_rows, TEST_QUERY, industry="finance")
        # 应正确处理，不崩溃
        assert result["total_loans"] == 1
        assert result["npl_ratio"] == 0  # 没有不良贷款


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
