"""Phase 7 主动学习单元测试

覆盖:
- feature flag 关闭 → 行为不变
- top-2 得分 gap < 阈值 → 反问
- gap >= 阈值 → 正常返回
- session 反问次数超限 → 不再反问
"""

from __future__ import annotations

from unittest import mock

import pytest

from learn.ingest.models import ClarificationRequest
from scripts.intent_parser import _check_active_learning, _score_intents


def _make_routing(intents=None):
    return {
        "intents": intents or [
            {
                "id": "intent_sales",
                "name": "销售趋势分析",
                "keywords": ["销售", "趋势", "营收"],
                "default_indicators": ["sales_amount", "order_count"],
                "analysis_type": "descriptive",
            },
            {
                "id": "intent_health",
                "name": "品类健康诊断",
                "keywords": ["品类", "健康", "毛利率"],
                "default_indicators": ["gross_margin_rate", "inventory_turnover"],
                "analysis_type": "diagnostic",
            },
            {
                "id": "intent_user",
                "name": "用户行为分析",
                "keywords": ["用户", "留存", "复购"],
                "default_indicators": ["retention_rate", "repurchase_rate"],
                "analysis_type": "descriptive",
            },
        ],
    }


# ============================================================
# _score_intents
# ============================================================


class TestScoreIntents:
    def test_scores_intents_by_keyword_match(self):
        routing = _make_routing()
        scored = _score_intents("销售趋势如何", routing)
        assert len(scored) >= 1
        assert scored[0][1]["id"] == "intent_sales"

    def test_empty_query_returns_empty(self):
        assert _score_intents("", _make_routing()) == []

    def test_no_keyword_match_returns_empty(self):
        routing = _make_routing()
        scored = _score_intents("xyz unknown abc", routing)
        assert scored == []

    def test_multiple_matches_sorted_by_score(self):
        routing = _make_routing()
        scored = _score_intents("销售和品类的问题", routing)
        assert len(scored) >= 2
        # "品类" (2 chars) + "销售" (2 chars) — both same length
        # but "品类" matched in intent_health, "销售" in intent_sales
        assert scored[0][0] >= scored[1][0]


# ============================================================
# _check_active_learning
# ============================================================


class TestCheckActiveLearning:
    def test_disabled_returns_none(self):
        routing = _make_routing()
        with mock.patch(
            "scripts.intent_parser._load_active_learning_config",
            return_value={"enabled": False, "confidence_gap_threshold": 0.10,
                          "max_clarifications_per_session": 3},
        ):
            result = _check_active_learning("销售品类分析", routing, 0)
            assert result is None

    def test_enabled_with_close_gap_returns_clarification(self):
        routing = _make_routing([
            {
                "id": "intent_a", "name": "销售分析",
                "keywords": ["销售", "渠道"], "default_indicators": ["sales_amount"],
            },
            {
                "id": "intent_b", "name": "品类分析",
                "keywords": ["品类", "渠道"], "default_indicators": ["order_count"],
            },
        ])
        with mock.patch(
            "scripts.intent_parser._load_active_learning_config",
            return_value={"enabled": True, "confidence_gap_threshold": 0.30,
                          "max_clarifications_per_session": 3},
        ):
            # query contains "渠道" which matches both — close scores
            result = _check_active_learning("渠道数据", routing, 0)
            assert isinstance(result, ClarificationRequest)
            assert len(result.options) == 2
            assert result.gap < 0.30

    def test_enabled_with_large_gap_returns_none(self):
        routing = _make_routing([
            {
                "id": "intent_a", "name": "销售分析",
                "keywords": ["销售", "营收", "订单", "金额", "渠道"], "default_indicators": [],
            },
            {
                "id": "intent_b", "name": "品类分析",
                "keywords": ["品类"], "default_indicators": [],
            },
        ])
        with mock.patch(
            "scripts.intent_parser._load_active_learning_config",
            return_value={"enabled": True, "confidence_gap_threshold": 0.10,
                          "max_clarifications_per_session": 3},
        ):
            # query matches 4 keywords from intent_a vs 1 from intent_b → large gap
            result = _check_active_learning("销售渠道营收订单", routing, 0)
            assert result is None

    def test_max_clarifications_reached_returns_none(self):
        routing = _make_routing([
            {"id": "intent_a", "name": "A", "keywords": ["x"], "default_indicators": []},
            {"id": "intent_b", "name": "B", "keywords": ["x"], "default_indicators": []},
        ])
        with mock.patch(
            "scripts.intent_parser._load_active_learning_config",
            return_value={"enabled": True, "confidence_gap_threshold": 0.30,
                          "max_clarifications_per_session": 3},
        ):
            result = _check_active_learning("x", routing, 3)
            assert result is None

    def test_only_one_intent_matched_returns_none(self):
        routing = _make_routing()
        with mock.patch(
            "scripts.intent_parser._load_active_learning_config",
            return_value={"enabled": True, "confidence_gap_threshold": 0.30,
                          "max_clarifications_per_session": 3},
        ):
            result = _check_active_learning("销售", routing, 0)
            assert result is None  # Only "intent_sales" matches

    def test_gap_calculation_normalized(self):
        """gap = (top_score - second_score) / top_score, normalized to [0,1]"""
        routing = _make_routing([
            {"id": "intent_a", "name": "A", "keywords": ["销售", "趋势"], "default_indicators": []},
            {"id": "intent_b", "name": "B", "keywords": ["销售"], "default_indicators": []},
        ])
        with mock.patch(
            "scripts.intent_parser._load_active_learning_config",
            return_value={"enabled": True, "confidence_gap_threshold": 0.60,
                          "max_clarifications_per_session": 3},
        ):
            # top_score = 4 (销售+趋势, 2 chars each), second = 2 (销售, 2 chars)
            # gap = (4-2)/4 = 0.50 < 0.60 → should trigger
            result = _check_active_learning("销售趋势", routing, 0)
            assert isinstance(result, ClarificationRequest)
            assert result.gap == pytest.approx(0.50)
