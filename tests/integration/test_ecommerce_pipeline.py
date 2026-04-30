# -*- coding: utf-8 -*-
"""
电商端到端管道集成测试
测试用例: TC-PIPE-001 ~ TC-PIPE-006

验证输入→输出全流程:
  用户查询 → 上下文检索 → 数据加载 → 分析 → 安全扫描
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ecommerce_pipeline import (
    run_pipeline,
    step1_retrieve_context,
    step2_load_data,
    step3_analyze,
    step4_security_scan,
)

TEST_CSV = str(PROJECT_ROOT / "tests" / "data" / "sample" / "test_orders.csv")
TEST_QUERY = "各品类 GMV 和订单量"


class TestEcommercePipeline:
    """电商数据管道全链路测试"""

    def test_pipeline_full_flow(self):
        """TC-PIPE-001: 全链路运行验证"""
        result = run_pipeline(TEST_QUERY, TEST_CSV)

        # 基本结构
        assert result["pipeline"] == "ecommerce"
        assert result["query"] == TEST_QUERY

        # 所有步骤都存在
        steps = result["steps"]
        assert "context_retrieval" in steps
        assert "data_loading" in steps
        assert "analysis" in steps
        assert "security" in steps

        # 执行时间合理
        assert result["timing"]["total_ms"] > 0
        assert len(result["timing"]["breakdown"]) == 4

        # 汇总信息
        summary = result["summary"]
        assert summary["total_rows_loaded"] > 0
        assert summary["total_gmv"] > 0
        assert summary["total_orders"] > 0
        assert summary["categories"] > 0
        assert summary["security_pass"] is True
        assert summary["security_level"] == "LOW"

    def test_pipeline_output_schema(self):
        """TC-PIPE-002: 输出 JSON Schema 验证"""
        result = run_pipeline(TEST_QUERY, TEST_CSV)

        # 顶级字段
        assert set(result.keys()) == {"pipeline", "query", "steps", "output",
                                       "timing", "summary"}

        # steps 结构
        steps = result["steps"]
        assert "indicators" in steps["context_retrieval"]
        assert "scenarios" in steps["context_retrieval"]
        assert "source" in steps["data_loading"]
        assert "total_rows" in steps["data_loading"]
        assert "total_gmv" in steps["analysis"]
        assert "total_orders" in steps["analysis"]
        assert "category_breakdown" in steps["analysis"]
        assert isinstance(steps["security"]["pass"], bool)

        # category_breakdown 中每条记录的 schema
        for item in steps["analysis"]["category_breakdown"]:
            assert set(item.keys()) == {"category", "gmv", "order_count",
                                         "gmv_share_pct"}
            assert item["gmv"] >= 0
            assert item["order_count"] >= 1
            assert 0 <= item["gmv_share_pct"] <= 100

        # output 结构与 category_breakdown 相同（经过 security 清洗）
        for item in result["output"]:
            assert set(item.keys()) == {"category", "gmv", "order_count",
                                         "gmv_share_pct"}

    def test_step1_context_retrieval(self):
        """TC-PIPE-003: 上下文检索 — 返回电商相关指标和场景"""
        context = step1_retrieve_context(TEST_QUERY, "ecommerce")

        assert "indicators" in context
        assert "scenarios" in context
        assert len(context["indicators"]) > 0
        assert len(context["scenarios"]) > 0

        # 应包含核心电商指标
        indicator_codes = {i.get("code") for i in context["indicators"]}
        assert "sales_amount" in indicator_codes, "缺少销售额指标"
        assert "order_count" in indicator_codes, "缺少订单量指标"

        # 每个指标必有定义信息
        for ind in context["indicators"]:
            assert ind.get("code")
            assert ind.get("name")
            assert ind.get("table_name")

        assert context["method"] == "fts+vector+rrf+temporal"

    def test_step2_data_loading_bom_handling(self):
        """TC-PIPE-004: 数据加载 — 正确处理 UTF-8 BOM"""
        rows = step2_load_data(TEST_CSV, required_fields=[
            "order_id", "category", "actual_amount",
        ])
        assert len(rows) > 0

        # BOM 必须正确处理 — order_id key 中不含 BOM
        first_row = rows[0]
        assert "order_id" in first_row, "BOM 导致 order_id 列名带前缀"
        assert first_row["order_id"].startswith("O2024")

    def test_step3_analysis_aggregation(self):
        """TC-PIPE-005: 数据分析 — 品类聚合计算"""
        rows = step2_load_data(TEST_CSV)
        result = step3_analyze(rows, TEST_QUERY)

        assert result["total_orders"] == len(rows)
        assert result["total_gmv"] > 0
        assert len(result["category_breakdown"]) > 0

        # GMV 占比之和约等于 100%
        total_share = sum(b["gmv_share_pct"] for b in result["category_breakdown"])
        assert abs(total_share - 100.0) < 1.0, \
            f"GMV 占比之和应为 100%，实际为 {total_share}"

        # GMV 降序排列
        gmvs = [b["gmv"] for b in result["category_breakdown"]]
        assert gmvs == sorted(gmvs, reverse=True), "品类应按 GMV 降序排列"

        # 各品类订单数之和 = 总订单数
        order_sum = sum(b["order_count"] for b in result["category_breakdown"])
        assert order_sum == result["total_orders"]

    def test_step4_security_scan_low(self):
        """TC-PIPE-006: 安全扫描 — 聚合输出无敏感数据"""
        result = run_pipeline(TEST_QUERY, TEST_CSV)
        assert result["steps"]["security"]["pass"] is True
        assert result["steps"]["security"]["level"] == "LOW"
        assert result["steps"]["security"]["blocked"] == []
        # 聚合数据不含 P1 字段，不应触发脱敏
        assert result["steps"]["security"]["masked"] == []


class TestEcommercePipelineEdgeCases:
    """边缘场景测试"""

    def test_pipeline_with_unknown_industry(self):
        """未知行业应返回空上下文但不中断"""
        result = run_pipeline(TEST_QUERY, TEST_CSV, industry="unknown")
        assert result["pipeline"] == "unknown"
        assert len(result["steps"]["context_retrieval"]["indicators"]) == 0
        # 管道应该继续执行
        assert result["summary"]["total_rows_loaded"] > 0
        assert result["summary"]["total_gmv"] > 0

    def test_pipeline_single_record(self):
        """单行数据也应正确聚合"""
        rows = step2_load_data(TEST_CSV)
        single_row = [rows[0]]
        result = step3_analyze(single_row, TEST_QUERY)

        assert result["total_orders"] == 1
        assert result["total_gmv"] > 0
        assert len(result["category_breakdown"]) == 1
        assert result["category_breakdown"][0]["gmv_share_pct"] == 100.0

    def test_pipeline_analysis_no_mutation(self):
        """step3_analyze 不应修改输入数据"""
        rows = step2_load_data(TEST_CSV)
        original_len = len(rows)
        original_first = dict(rows[0])

        step3_analyze(rows, TEST_QUERY)

        assert len(rows) == original_len, "输入数据不应被修改"
        assert rows[0] == original_first, "输入数据不应被修改"

    def test_pipeline_csv_not_found(self):
        """CSV 不存在时应抛出明确的 FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            step2_load_data("nonexistent.csv")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
