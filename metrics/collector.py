"""
度量收集器

SQLite 持久化，记录:
- 每次管道运行的响应时间 (按步骤细分)
- 检索准确率 (返回的指标/场景数量，top score)
- 安全拦截次数 (blocked, masked, level)

用法:
    collector = MetricsCollector()
    collector.record_run({
        "pipeline": "ecommerce",
        "query": "各品类 GMV",
        "timing": {"total_ms": 1234, "breakdown": {...}},
        "retrieval": {"indicators": 3, "scenarios": 2, "top_score": 0.85},
        "security": {"pass": True, "level": "LOW", "blocked": [], "masked": []},
    })
    recent = collector.get_recent_runs(limit=10)
    stats = collector.get_stats()
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional


class MetricsCollector:
    """度量收集器 — SQLite 持久化"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(
            Path(__file__).resolve().parent.parent / "data" / "metrics.db"
        )
        self._ensure_tables()

    # ==================== 初始化 ====================

    def _ensure_tables(self):
        """创建度量表"""
        conn = self._connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline TEXT NOT NULL,
                query TEXT,
                timestamp TEXT NOT NULL,
                total_ms REAL,
                step_retrieval_ms REAL,
                step_loading_ms REAL,
                step_analysis_ms REAL,
                step_security_ms REAL,
                retrieval_indicators INTEGER,
                retrieval_scenarios INTEGER,
                retrieval_top_score REAL,
                security_pass INTEGER,
                security_level TEXT,
                security_blocked INTEGER DEFAULT 0,
                security_masked INTEGER DEFAULT 0,
                rows_loaded INTEGER,
                run_status TEXT DEFAULT 'success'
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_runs INTEGER DEFAULT 0,
                avg_total_ms REAL DEFAULT 0,
                avg_retrieval_ms REAL DEFAULT 0,
                avg_loading_ms REAL DEFAULT 0,
                avg_analysis_ms REAL DEFAULT 0,
                avg_security_ms REAL DEFAULT 0,
                total_blocked INTEGER DEFAULT 0,
                total_masked INTEGER DEFAULT 0,
                avg_retrieval_indicators REAL DEFAULT 0,
                avg_retrieval_scenarios REAL DEFAULT 0,
                created TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pipeline TEXT,
                query TEXT,
                event_type TEXT NOT NULL,
                level TEXT,
                detail TEXT
            )
        """)

        conn.commit()
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    # ==================== 记录 ====================

    def record_run(self, result: dict) -> int:
        """
        记录一次管道运行度量

        Args:
            result: run_pipeline() 的输出字典

        Returns:
            记录的 ID
        """
        steps = result.get("steps", {})
        timing = result.get("timing", {})
        summary = result.get("summary", {})
        breakdown = timing.get("breakdown", {})

        retrieval = steps.get("context_retrieval", {})
        security = steps.get("security", {})

        top_score = 0.0
        scores = retrieval.get("scores") or {}
        ind_scores = scores.get("indicators", [])
        if ind_scores:
            top_score = ind_scores[0][1] if len(ind_scores[0]) > 1 else 0

        conn = self._connect()
        conn.execute("""
            INSERT INTO pipeline_runs (
                pipeline, query, timestamp, total_ms,
                step_retrieval_ms, step_loading_ms, step_analysis_ms, step_security_ms,
                retrieval_indicators, retrieval_scenarios, retrieval_top_score,
                security_pass, security_level, security_blocked, security_masked,
                rows_loaded, run_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.get("pipeline", "unknown"),
            result.get("query", ""),
            datetime.now().isoformat(),
            timing.get("total_ms", 0),
            breakdown.get("context_retrieval", 0),
            breakdown.get("data_loading", 0),
            breakdown.get("analysis", 0),
            breakdown.get("security", 0),
            len(retrieval.get("indicators", [])),
            len(retrieval.get("scenarios", [])),
            top_score,
            1 if security.get("pass", True) else 0,
            security.get("level", "LOW"),
            len(security.get("blocked", [])),
            len(security.get("masked", [])),
            summary.get("total_rows_loaded", 0),
            "success"
        ))
        record_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # 记录安全事件
        for blocked in security.get("blocked", []):
            conn.execute("""
                INSERT INTO security_events (timestamp, pipeline, query, event_type, level, detail)
                VALUES (?, ?, ?, 'blocked', 'CRITICAL', ?)
            """, (datetime.now().isoformat(), result.get("pipeline"),
                  result.get("query"), str(blocked)))

        for masked in security.get("masked", []):
            conn.execute("""
                INSERT INTO security_events (timestamp, pipeline, query, event_type, level, detail)
                VALUES (?, ?, ?, 'masked', 'HIGH', ?)
            """, (datetime.now().isoformat(), result.get("pipeline"),
                  result.get("query"), str(masked)))

        conn.commit()
        conn.close()
        return record_id

    def record_error(self, pipeline: str, query: str, error: str):
        """记录管道执行错误"""
        conn = self._connect()
        conn.execute("""
            INSERT INTO pipeline_runs (
                pipeline, query, timestamp, total_ms,
                retrieval_indicators, retrieval_scenarios,
                security_pass, run_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pipeline, query, datetime.now().isoformat(), 0,
            0, 0, 0, f"error: {error[:200]}"
        ))
        conn.commit()
        conn.close()

    # ==================== 查询 ====================

    def get_recent_runs(self, limit: int = 20) -> List[Dict]:
        """获取最近 N 次运行记录"""
        conn = self._connect()
        columns = [desc[0] for desc in conn.execute(
            "SELECT * FROM pipeline_runs LIMIT 1").description]
        rows = conn.execute("""
            SELECT * FROM pipeline_runs
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(zip(columns, r)) for r in rows]

    def get_stats(self, since: str = None) -> Dict:
        """
        获取聚合统计

        Args:
            since: ISO 日期起始 (如 "2026-04-01")，默认最近 7 天

        Returns:
            统计字典
        """
        if not since:
            since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        conn = self._connect()

        total = conn.execute("""
            SELECT COUNT(*) FROM pipeline_runs WHERE timestamp >= ?
        """, (since,)).fetchone()[0]

        avg_timing = conn.execute("""
            SELECT
                AVG(total_ms), AVG(step_retrieval_ms), AVG(step_loading_ms),
                AVG(step_analysis_ms), AVG(step_security_ms)
            FROM pipeline_runs WHERE timestamp >= ? AND run_status = 'success'
        """, (since,)).fetchone()

        security_stats = conn.execute("""
            SELECT
                COUNT(*) FILTER (WHERE security_pass = 1),
                COUNT(*) FILTER (WHERE security_pass = 0),
                SUM(security_blocked), SUM(security_masked)
            FROM pipeline_runs WHERE timestamp >= ?
        """, (since,)).fetchone()

        by_pipeline = conn.execute("""
            SELECT pipeline, COUNT(*) as cnt,
                   ROUND(AVG(total_ms), 2) as avg_ms
            FROM pipeline_runs WHERE timestamp >= ?
            GROUP BY pipeline ORDER BY cnt DESC
        """, (since,)).fetchall()

        by_level = conn.execute("""
            SELECT security_level, COUNT(*) as cnt
            FROM pipeline_runs WHERE timestamp >= ?
            GROUP BY security_level ORDER BY cnt DESC
        """, (since,)).fetchall()

        conn.close()

        return {
            "period": {"since": since, "until": datetime.now().isoformat()},
            "total_runs": total,
            "successful_runs": security_stats[0] if security_stats else 0,
            "blocked_runs": security_stats[1] if security_stats else 0,
            "avg_timing_ms": {
                "total": round(avg_timing[0] or 0, 2),
                "retrieval": round(avg_timing[1] or 0, 2),
                "loading": round(avg_timing[2] or 0, 2),
                "analysis": round(avg_timing[3] or 0, 2),
                "security": round(avg_timing[4] or 0, 2),
            } if avg_timing else {},
            "security": {
                "total_blocked": security_stats[2] or 0,
                "total_masked": security_stats[3] or 0,
            } if security_stats else {},
            "by_pipeline": [{"pipeline": r[0], "count": r[1], "avg_ms": r[2]} for r in by_pipeline],
            "by_level": [{"level": r[0], "count": r[1]} for r in by_level],
        }

    def get_daily_stats(self, days: int = 30) -> List[Dict]:
        """获取每日聚合统计"""
        conn = self._connect()
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        rows = conn.execute("""
            SELECT
                date(timestamp) as day,
                COUNT(*) as runs,
                ROUND(AVG(total_ms), 2) as avg_ms,
                SUM(CASE WHEN security_pass = 0 THEN 1 ELSE 0 END) as blocked,
                SUM(security_masked) as masked,
                ROUND(AVG(retrieval_indicators), 2) as avg_indicators
            FROM pipeline_runs
            WHERE timestamp >= ?
            GROUP BY date(timestamp)
            ORDER BY day
        """, (since,)).fetchall()

        conn.close()
        return [
            {
                "date": r[0],
                "runs": r[1],
                "avg_response_ms": r[2],
                "blocked": r[3],
                "masked": r[4],
                "avg_indicators": r[5],
            }
            for r in rows
        ]

    def get_security_events(self, limit: int = 50) -> List[Dict]:
        """获取最近安全事件"""
        conn = self._connect()
        columns = [desc[0] for desc in conn.execute(
            "SELECT * FROM security_events LIMIT 1").description]
        rows = conn.execute("""
            SELECT * FROM security_events
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(zip(columns, r)) for r in rows]

    def clear(self):
        """清空所有度量数据"""
        conn = self._connect()
        conn.execute("DELETE FROM pipeline_runs")
        conn.execute("DELETE FROM daily_stats")
        conn.execute("DELETE FROM security_events")
        conn.commit()
        conn.close()

    def __repr__(self):
        return f"MetricsCollector(db='{self.db_path}')"
