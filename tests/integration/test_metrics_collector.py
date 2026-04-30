# -*- coding: utf-8 -*-
"""
度量收集器单元测试

测试 MetricsCollector 的:
- 记录管道运行度量
- 查询聚合统计
- 每日统计
- 安全事件记录
- 边界情况处理
"""

import sys
import tempfile
import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from metrics.collector import MetricsCollector


@pytest.fixture
def collector():
    """创建临时 MetricsCollector 实例"""
    db_path = os.path.join(tempfile.gettempdir(), "test_metrics_collector.db")
    c = MetricsCollector(db_path)
    c.clear()
    yield c
    c.clear()
    try:
        os.unlink(db_path)
    except OSError:
        pass


SAMPLE_RUN = {
    "pipeline": "ecommerce",
    "query": "各品类 GMV",
    "steps": {
        "context_retrieval": {
            "indicators": [{"code": "sales_amount"}],
            "scenarios": [{"code": "sales_trend"}],
        },
        "data_loading": {},
        "analysis": {},
        "security": {"pass": True, "level": "LOW", "blocked": [], "masked": []},
    },
    "timing": {
        "total_ms": 150.0,
        "breakdown": {
            "context_retrieval": 20.0,
            "data_loading": 30.0,
            "analysis": 50.0,
            "security": 50.0,
        },
    },
    "summary": {
        "total_rows_loaded": 1000,
        "total_indicators": 1,
        "total_scenarios": 1,
    },
}

SAMPLE_RUN_WITH_BLOCKED = {
    "pipeline": "finance",
    "query": "查询",
    "steps": {
        "context_retrieval": {"indicators": [], "scenarios": []},
        "data_loading": {},
        "analysis": {},
        "security": {
            "pass": False,
            "level": "CRITICAL",
            "blocked": ["P0-BLOCKED: 身份证号 in field 'id_card'"],
            "masked": [],
        },
    },
    "timing": {
        "total_ms": 50.0,
        "breakdown": {},
    },
    "summary": {
        "total_rows_loaded": 10,
        "total_indicators": 0,
        "total_scenarios": 0,
    },
}


class TestMetricsCollector:
    """度量收集器核心功能测试"""

    def test_record_run(self, collector):
        """TC-MET-001: 记录正常管道运行"""
        rid = collector.record_run(SAMPLE_RUN)
        assert rid > 0

        recent = collector.get_recent_runs(limit=10)
        assert len(recent) >= 1
        assert recent[0]["pipeline"] == "ecommerce"
        assert recent[0]["total_ms"] == 150.0

    def test_record_run_with_blocked(self, collector):
        """TC-MET-002: 记录被拦截的管道运行"""
        rid = collector.record_run(SAMPLE_RUN_WITH_BLOCKED)
        assert rid > 0

        recent = collector.get_recent_runs(limit=10)
        blocked = [r for r in recent if r["security_pass"] == 0]
        assert len(blocked) >= 1

        events = collector.get_security_events()
        block_events = [e for e in events if e["event_type"] == "blocked"]
        assert len(block_events) >= 1

    def test_get_stats(self, collector):
        """TC-MET-003: 聚合统计计算正确"""
        collector.record_run(SAMPLE_RUN)
        collector.record_run(SAMPLE_RUN)

        stats = collector.get_stats()
        assert stats["total_runs"] == 2
        assert stats["successful_runs"] == 2
        assert stats["avg_timing_ms"]["total"] == 150.0
        assert stats["avg_timing_ms"]["retrieval"] == 20.0

    def test_get_stats_with_blocked(self, collector):
        """TC-MET-004: 包含拦截数据的统计"""
        collector.record_run(SAMPLE_RUN)
        collector.record_run(SAMPLE_RUN_WITH_BLOCKED)

        stats = collector.get_stats()
        assert stats["total_runs"] == 2
        assert stats["successful_runs"] == 1
        assert stats["blocked_runs"] == 1
        assert stats["security"]["total_blocked"] == 1

    def test_get_daily_stats(self, collector):
        """TC-MET-005: 每日统计返回正确"""
        collector.record_run(SAMPLE_RUN)
        collector.record_run(SAMPLE_RUN)

        daily = collector.get_daily_stats(days=30)
        assert len(daily) >= 1
        assert daily[0]["runs"] == 2
        assert daily[0]["avg_response_ms"] == 150.0

    def test_get_security_events(self, collector):
        """TC-MET-006: 安全事件记录"""
        collector.record_run(SAMPLE_RUN_WITH_BLOCKED)

        events = collector.get_security_events()
        assert len(events) >= 1
        assert events[0]["event_type"] == "blocked"
        assert events[0]["level"] == "CRITICAL"

    def test_record_error(self, collector):
        """TC-MET-007: 记录错误运行"""
        collector.record_error("test_pipeline", "测试查询", "连接超时")

        recent = collector.get_recent_runs(limit=10)
        errors = [r for r in recent if "error" in r.get("run_status", "")]
        assert len(errors) >= 1

    def test_clear(self, collector):
        """TC-MET-008: 清空度量数据"""
        collector.record_run(SAMPLE_RUN)
        assert collector.get_stats()["total_runs"] > 0

        collector.clear()
        assert collector.get_stats()["total_runs"] == 0
        assert len(collector.get_security_events()) == 0

    def test_by_pipeline_stats(self, collector):
        """TC-MET-009: 按行业分组统计"""
        collector.record_run(SAMPLE_RUN)

        run2 = dict(SAMPLE_RUN)
        run2["pipeline"] = "finance"
        collector.record_run(run2)

        stats = collector.get_stats()
        pipelines = {p["pipeline"] for p in stats["by_pipeline"]}
        assert "ecommerce" in pipelines
        assert "finance" in pipelines

    def test_by_level_stats(self, collector):
        """TC-MET-010: 按安全级别分组统计"""
        collector.record_run(SAMPLE_RUN)
        collector.record_run(SAMPLE_RUN_WITH_BLOCKED)

        stats = collector.get_stats()
        levels = {l["level"] for l in stats["by_level"]}
        assert "LOW" in levels
        assert "CRITICAL" in levels


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
