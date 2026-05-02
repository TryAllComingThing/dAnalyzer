"""
industry_analyzers 单元测试 — 电商/物流/金融/制造分析函数

测试 scripts/industry_analyzers.py 的纯分析函数.
不依赖 LLM, 纯数据驱动.
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.industry_analyzers import (
    analyze_ecommerce,
    analyze_logistics,
    analyze_finance,
    analyze_manufacturing,
    analyze_for_industry,
    ANALYZER_MAP,
)


# ── Fixtures ────────────────────────────────────────────────────

@pytest.fixture
def ecommerce_rows():
    return [
        {"order_id": "O1", "category": "食品饮料", "actual_amount": "100", "user_id": "U1"},
        {"order_id": "O2", "category": "食品饮料", "actual_amount": "50", "user_id": "U2"},
        {"order_id": "O3", "category": "美妆护肤", "actual_amount": "200", "user_id": "U1"},
        {"order_id": "O4", "category": "美妆护肤", "actual_amount": "300", "user_id": "U3"},
        {"order_id": "O5", "category": "数码产品", "actual_amount": "350", "user_id": "U2"},
    ]


@pytest.fixture
def logistics_rows():
    return [
        {"waybill_id": "W1", "status": "已签收", "weight": "5.0",
         "pickup_time": "2024-01-01 08:00", "sign_time": "2024-01-02 10:00"},
        {"waybill_id": "W2", "status": "运输中", "weight": "3.5",
         "pickup_time": "2024-01-02 09:00", "sign_time": ""},
        {"waybill_id": "W3", "status": "已签收", "weight": "10.0",
         "pickup_time": "2024-01-01 12:00", "sign_time": "2024-01-03 15:00"},
    ]


@pytest.fixture
def finance_rows():
    return [
        {"loan_id": "L1", "balance": "100000", "loan_amount": "200000",
         "classification": "正常", "status": "正常还款"},
        {"loan_id": "L2", "balance": "50000", "loan_amount": "100000",
         "classification": "次级", "status": "逾期"},
        {"loan_id": "L3", "balance": "20000", "loan_amount": "50000",
         "classification": "可疑", "status": "催收"},
    ]


@pytest.fixture
def manufacturing_rows():
    return [
        {"order_id": "M1", "planned_qty": "100", "actual_qty": "95",
         "defect_qty": "5", "rework_qty": "2"},
        {"order_id": "M2", "planned_qty": "200", "actual_qty": "180",
         "defect_qty": "10", "rework_qty": "3"},
    ]


# ── Ecommerce Tests ─────────────────────────────────────────────

class TestEcommerce:
    def test_basic_aggregation(self, ecommerce_rows):
        r = analyze_ecommerce(ecommerce_rows, "")
        assert r["total_orders"] == 5
        assert r["total_gmv"] == 1000.0  # 100+50+200+300+350
        assert len(r["category_breakdown"]) == 3

    def test_gmv_sorted_desc(self, ecommerce_rows):
        r = analyze_ecommerce(ecommerce_rows, "")
        gmvs = [c["gmv"] for c in r["category_breakdown"]]
        assert gmvs == sorted(gmvs, reverse=True)

    def test_gmv_share_sums_to_100(self, ecommerce_rows):
        r = analyze_ecommerce(ecommerce_rows, "")
        total_share = sum(c["gmv_share_pct"] for c in r["category_breakdown"])
        assert abs(total_share - 100.0) < 0.5

    def test_missing_category_defaults_unknown(self):
        """category 字段缺失时默认 '未知'"""
        rows = [{"actual_amount": "100"}]  # 无 category 键
        r = analyze_ecommerce(rows, "")
        assert r["category_breakdown"][0]["category"] == "未知"

    def test_invalid_amount(self):
        rows = [{"category": "食品", "actual_amount": "not_a_number"}]
        r = analyze_ecommerce(rows, "")
        assert r["total_gmv"] == 0.0

    def test_empty_rows(self):
        r = analyze_ecommerce([], "")
        assert r["total_gmv"] == 0.0
        assert r["total_orders"] == 0
        assert r["category_breakdown"] == []

    def test_single_row(self):
        rows = [{"category": "食品", "actual_amount": "100"}]
        r = analyze_ecommerce(rows, "")
        assert r["total_orders"] == 1
        assert r["total_gmv"] == 100.0
        assert r["category_breakdown"][0]["gmv_share_pct"] == 100.0


# ── Logistics Tests ─────────────────────────────────────────────

class TestLogistics:
    def test_basic_stats(self, logistics_rows):
        r = analyze_logistics(logistics_rows, "")
        assert r["total_waybills"] == 3
        assert r["delivered"] == 2
        assert r["delivery_rate"] == round(2/3*100, 1)
        assert r["in_transit"] == 1

    def test_weight_sum(self, logistics_rows):
        r = analyze_logistics(logistics_rows, "")
        assert r["total_weight_kg"] == 18.5

    def test_avg_delivery_hours(self, logistics_rows):
        r = analyze_logistics(logistics_rows, "")
        assert r["avg_delivery_hours"] > 0

    def test_empty_rows(self):
        r = analyze_logistics([], "")
        assert r["total_waybills"] == 0
        assert r["delivery_rate"] == 0

    def test_missing_status_field(self):
        rows = [{"waybill_id": "W1", "weight": "5"}]
        r = analyze_logistics(rows, "")
        assert r["total_waybills"] == 1
        assert r["delivered"] == 0
        assert r["in_transit"] == 0

    def test_invalid_weight(self):
        rows = [{"status": "已签收", "weight": "heavy",
                 "pickup_time": "2024-01-01 08:00", "sign_time": "2024-01-02 10:00"}]
        r = analyze_logistics(rows, "")
        assert r["total_weight_kg"] == 0.0
        assert r["delivery_rate"] == 100.0  # delivered still counted

    def test_single_row_delivered(self):
        rows = [{"status": "已签收", "weight": "2.5",
                 "pickup_time": "2024-01-01 08:00", "sign_time": "2024-01-02 10:00"}]
        r = analyze_logistics(rows, "")
        assert r["delivery_rate"] == 100.0
        assert r["delivered"] == 1
        assert r["avg_delivery_hours"] == 26.0


# ── Finance Tests ───────────────────────────────────────────────

class TestFinance:
    def test_basic_stats(self, finance_rows):
        r = analyze_finance(finance_rows, "")
        assert r["total_loans"] == 3
        assert r["total_balance"] == 170000.0

    def test_npl_calculation(self, finance_rows):
        r = analyze_finance(finance_rows, "")
        # NPL = 次级(50000) + 可疑(20000) = 70000
        assert r["npl_balance"] == 70000.0
        assert r["npl_ratio"] == round(70000 / 170000 * 100, 2)

    def test_classification_distribution(self, finance_rows):
        r = analyze_finance(finance_rows, "")
        assert r["classification_distribution"]["正常"] == 1
        assert r["classification_distribution"]["次级"] == 1
        assert r["classification_distribution"]["可疑"] == 1

    def test_zero_balance(self):
        rows = [{"balance": "0", "loan_amount": "100", "classification": "正常", "status": "正常"}]
        r = analyze_finance(rows, "")
        assert r["npl_ratio"] == 0

    def test_missing_classification(self):
        rows = [{"balance": "1000", "loan_amount": "5000"}]
        r = analyze_finance(rows, "")
        assert r["classification_distribution"]["未知"] == 1
        assert r["npl_balance"] == 0  # "未知" not in NPL list

    def test_invalid_numeric_fields(self):
        rows = [{"balance": "abc", "loan_amount": "xyz",
                 "classification": "正常"}]
        r = analyze_finance(rows, "")
        assert r["total_balance"] == 0.0
        assert r["total_loan_amount"] == 0.0


# ── Manufacturing Tests ─────────────────────────────────────────

class TestManufacturing:
    def test_basic_stats(self, manufacturing_rows):
        r = analyze_manufacturing(manufacturing_rows, "")
        assert r["total_orders"] == 2
        assert r["total_planned"] == 300
        assert r["total_actual"] == 275
        assert r["total_defect"] == 15

    def test_rates(self, manufacturing_rows):
        r = analyze_manufacturing(manufacturing_rows, "")
        assert r["capacity_utilization_pct"] == round(275 / 300 * 100, 1)
        assert r["defect_rate_pct"] == round(15 / 275 * 100, 2)
        assert r["yield_rate_pct"] == round((275 - 15) / 275 * 100, 1)

    def test_zero_planned(self):
        rows = [{"planned_qty": "0", "actual_qty": "0", "defect_qty": "0", "rework_qty": "0"}]
        r = analyze_manufacturing(rows, "")
        assert r["capacity_utilization_pct"] == 0
        assert r["defect_rate_pct"] == 0

    def test_missing_fields(self):
        rows = [{"order_id": "M1"}]  # no planned_qty, actual_qty, defect_qty, rework_qty
        r = analyze_manufacturing(rows, "")
        assert r["total_orders"] == 1
        assert r["total_planned"] == 0
        assert r["total_actual"] == 0
        assert r["defect_rate_pct"] == 0

    def test_defect_exceeds_actual(self):
        rows = [{"planned_qty": "100", "actual_qty": "50",
                 "defect_qty": "60", "rework_qty": "0"}]
        r = analyze_manufacturing(rows, "")
        # yield_rate = (50 - 60) / 50 * 100 = -20.0
        assert r["yield_rate_pct"] == -20.0
        assert r["defect_rate_pct"] == 120.0


# ── Analyze for Industry ────────────────────────────────────────

class TestAnalyzeForIndustry:
    def test_routes_to_fmcg(self, ecommerce_rows):
        r = analyze_for_industry(ecommerce_rows, "", "fmcg")
        assert "total_gmv" in r

    def test_old_industry_falls_back_to_default(self, logistics_rows):
        """Old industry codes not in ANALYZER_MAP fall back to fmcg analyzer"""
        r = analyze_for_industry(logistics_rows, "", "logistics")
        assert "total_gmv" in r

    def test_unknown_industry_defaults_to_fmcg(self, ecommerce_rows):
        r = analyze_for_industry(ecommerce_rows, "", "unknown_industry")
        assert "total_gmv" in r

    def test_fmcg_is_in_analyzer_map(self):
        assert "fmcg" in ANALYZER_MAP


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
