"""
dAnalyzer 行业数据存储模块 — 核心

混合存储引擎: YAML 编辑 + SQLite 检索
YAML → 人类编辑格式，SQLite → 机器检索格式，同步由 sync.py 管理。
"""

import sqlite3
import json
import yaml
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class IndustryStore:
    """
    行业数据混合存储引擎

    YAML: 人类可读编辑格式
    SQLite: 高速检索引擎
    同步: 启动时增量同步（委托 sync.py）
    """

    def __init__(self, industry: str, data_root: str = "knowledge/industry"):
        self.industry = industry
        self.data_root = Path(data_root)
        self.yaml_path = self.data_root / industry
        self.db_path = self.data_root / f"{industry}.db"
        self._cache = {}

        self._ensure_init()

    # ==================== 初始化 ====================

    def _ensure_init(self):
        """确保数据库已初始化"""
        if not self.db_path.exists() or self._needs_sync():
            from .sync import sync_from_yaml
            sync_from_yaml(self.yaml_path, self.db_path, self.industry)
            self._cache.clear()

    def _needs_sync(self) -> bool:
        """
        检查是否需要同步（mtime + 内容 hash 双重校验）
        mtime 变化但内容未变时不触发同步。
        """
        if not self.yaml_path.exists():
            return False

        if not self.db_path.exists():
            return True

        # 快速 mtime 检查
        db_mtime = self.db_path.stat().st_mtime
        yaml_mtime = 0
        for f in self.yaml_path.rglob("*.yaml"):
            if not f.name.startswith("_"):
                yaml_mtime = max(yaml_mtime, f.stat().st_mtime)

        if yaml_mtime <= db_mtime:
            return False

        # mtime 变了 → 检查内容 hash，避免无变更触发全量同步
        try:
            conn = sqlite3.connect(str(self.db_path))
            row = conn.execute(
                "SELECT file_hash FROM sync_meta LIMIT 1"
            ).fetchone()
            conn.close()
            if row:
                from .sync import calculate_yaml_hash
                return calculate_yaml_hash(self.yaml_path) != row[0]
        except Exception:
            pass

        return True

    # ==================== 检索接口 ====================

    def search(self, query: str, top_k: int = 5) -> Dict[str, List[Dict]]:
        """统一检索接口"""
        conn = sqlite3.connect(str(self.db_path))

        ind_columns = [
            desc[0] for desc in conn.execute("SELECT * FROM indicators LIMIT 1").description
        ]
        scn_columns = [
            desc[0] for desc in conn.execute("SELECT * FROM scenarios LIMIT 1").description
        ]

        indicators = conn.execute(
            """SELECT * FROM indicators
               WHERE keywords LIKE ? OR name LIKE ? OR description LIKE ?
               ORDER BY importance DESC, access_count DESC LIMIT ?""",
            (f"%{query}%", f"%{query}%", f"%{query}%", top_k),
        ).fetchall()

        scenarios = conn.execute(
            """SELECT * FROM scenarios
               WHERE keywords LIKE ? OR name LIKE ? OR description LIKE ?
               ORDER BY satisfaction DESC, usage_count DESC LIMIT ?""",
            (f"%{query}%", f"%{query}%", f"%{query}%", 3),
        ).fetchall()

        conn.close()

        return {
            "indicators": [self._row_to_dict(r, ind_columns) for r in indicators],
            "scenarios": [self._row_to_dict(r, scn_columns) for r in scenarios],
            "query": query,
            "count": {"indicators": len(indicators), "scenarios": len(scenarios)},
        }

    def _row_to_dict(self, row: Any, columns: tuple = None) -> Dict:
        """将行数据转换为字典"""
        if not row:
            return {}
        if isinstance(row, tuple):
            return dict(zip(columns, row)) if columns else dict(row)
        result = dict(row)
        for key in (
            "keywords", "relations", "required_indicators",
            "optional_indicators", "dimensions", "template",
            "preferred_dimensions", "frequent_queries", "frequent_scenarios",
        ):
            if key in result and result[key]:
                try:
                    result[key] = json.loads(result[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return result

    def get_indicator(self, code: str) -> Optional[Dict]:
        """获取单个指标"""
        conn = sqlite3.connect(str(self.db_path))
        columns = [
            desc[0] for desc in conn.execute("SELECT * FROM indicators LIMIT 1").description
        ]
        row = conn.execute("SELECT * FROM indicators WHERE code = ?", (code,)).fetchone()
        conn.close()
        return self._row_to_dict(row, columns) if row else None

    def get_scenario(self, code: str) -> Optional[Dict]:
        """获取单个场景"""
        conn = sqlite3.connect(str(self.db_path))
        columns = [
            desc[0] for desc in conn.execute("SELECT * FROM scenarios LIMIT 1").description
        ]
        row = conn.execute("SELECT * FROM scenarios WHERE code = ?", (code,)).fetchone()
        conn.close()
        return self._row_to_dict(row, columns) if row else None

    def get_preferences(self, user_id: str = "default") -> Optional[Dict]:
        """获取用户偏好"""
        conn = sqlite3.connect(str(self.db_path))
        columns = [
            desc[0] for desc in conn.execute("SELECT * FROM preferences LIMIT 1").description
        ]
        row = conn.execute(
            "SELECT * FROM preferences WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return self._row_to_dict(row, columns) if row else None

    def get_all_indicators(self) -> List[Dict]:
        """获取所有指标"""
        conn = sqlite3.connect(str(self.db_path))
        columns = [
            desc[0] for desc in conn.execute("SELECT * FROM indicators LIMIT 1").description
        ]
        rows = conn.execute(
            "SELECT * FROM indicators ORDER BY importance DESC, access_count DESC"
        ).fetchall()
        conn.close()
        return [self._row_to_dict(r, columns) for r in rows]

    def get_all_scenarios(self) -> List[Dict]:
        """获取所有场景"""
        conn = sqlite3.connect(str(self.db_path))
        columns = [
            desc[0] for desc in conn.execute("SELECT * FROM scenarios LIMIT 1").description
        ]
        rows = conn.execute(
            "SELECT * FROM scenarios ORDER BY satisfaction DESC, usage_count DESC"
        ).fetchall()
        conn.close()
        return [self._row_to_dict(r, columns) for r in rows]

    # ==================== 写入接口 ====================

    def update_preferences(self, user_id: str, updates: Dict):
        """更新用户偏好"""
        from .sync import sync_preferences_to_yaml

        conn = sqlite3.connect(str(self.db_path))
        existing = conn.execute(
            "SELECT * FROM preferences WHERE user_id = ?", (user_id,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE preferences SET default_industry = COALESCE(?, default_industry),
                   preferred_dimensions = COALESCE(?, preferred_dimensions),
                   default_time_range = COALESCE(?, default_time_range),
                   preferred_format = COALESCE(?, preferred_format),
                   updated = datetime('now') WHERE user_id = ?""",
                (
                    updates.get("default_industry"),
                    json.dumps(updates.get("preferred_dimensions"))
                    if updates.get("preferred_dimensions") else None,
                    updates.get("default_time_range"),
                    updates.get("preferred_format"),
                    user_id,
                ),
            )
        else:
            conn.execute(
                """INSERT INTO preferences (user_id, default_industry, preferred_dimensions,
                   default_time_range, preferred_format, updated)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (
                    user_id,
                    updates.get("default_industry"),
                    json.dumps(updates.get("preferred_dimensions", [])),
                    updates.get("default_time_range"),
                    updates.get("preferred_format"),
                ),
            )

        conn.commit()
        conn.close()
        sync_preferences_to_yaml(self.db_path, self.yaml_path)

    def record_query(self, user_id: str, query: str):
        """记录用户查询"""
        conn = sqlite3.connect(str(self.db_path))
        existing = conn.execute(
            "SELECT frequent_queries FROM preferences WHERE user_id = ?", (user_id,)
        ).fetchone()
        history = json.loads(existing[0]) if existing and existing[0] else []

        found = False
        for h in history:
            if h.get("query") == query:
                h["count"] = h.get("count", 0) + 1
                found = True
                break
        if not found:
            history.append({"query": query, "count": 1})

        history = sorted(history, key=lambda x: x["count"], reverse=True)[:10]
        conn.execute(
            "UPDATE preferences SET frequent_queries = ?, updated = datetime('now') WHERE user_id = ?",
            (json.dumps(history), user_id),
        )
        conn.commit()
        conn.close()

    # ==================== 工具方法 ====================

    def reload(self):
        """强制重新加载数据"""
        if self.db_path.exists():
            self.db_path.unlink()
        self._ensure_init()

    def get_stats(self) -> Dict:
        """获取统计信息"""
        conn = sqlite3.connect(str(self.db_path))
        stats = {
            "indicators": conn.execute("SELECT COUNT(*) FROM indicators").fetchone()[0],
            "scenarios": conn.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0],
            "preferences": conn.execute("SELECT COUNT(*) FROM preferences").fetchone()[0],
        }
        sync_meta = conn.execute("SELECT * FROM sync_meta").fetchall()
        stats["sync"] = [
            {"table_name": m[0], "last_sync": m[1], "record_count": m[2], "file_hash": m[3]}
            for m in sync_meta
        ]
        conn.close()
        return stats

    def __repr__(self):
        return f"IndustryStore(industry='{self.industry}', db='{self.db_path}')"


def get_store(industry: str = "fmcg", data_root: str = "knowledge/industry") -> IndustryStore:
    """获取行业存储实例"""
    return IndustryStore(industry, data_root)
