"""
dAnalyzer 行业数据存储模块

混合存储引擎: YAML 编辑 + SQLite 检索

设计原则:
- YAML: 人类可读，用于编辑
- SQLite: 高速检索，用于查询
- 自动同步: 启动时增量更新
"""

import sqlite3
import json
import yaml
import hashlib
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from functools import lru_cache


class IndustryStore:
    """
    行业数据混合存储引擎

    特性:
    - YAML 编辑: 人类可读，便于手动编辑
    - SQLite 检索: 高速查询，支持索引
    - 自动同步: 启动时检测变更并同步
    - 零依赖: 仅使用 Python 标准库
    """

    def __init__(self, industry: str, data_root: str = "data/industry"):
        """
        初始化存储引擎

        Args:
            industry: 行业名称 (如 ecommerce, logistics)
            data_root: 数据根目录路径
        """
        self.industry = industry
        self.data_root = Path(data_root)
        self.yaml_path = self.data_root / industry
        self.db_path = self.data_root / f"{industry}.db"

        # 缓存
        self._cache = {}

        # 启动时自动同步
        self._ensure_init()

    # ==================== 初始化 ====================

    def _ensure_init(self):
        """确保数据库已初始化"""
        if not self.db_path.exists() or self._needs_sync():
            self._sync_from_yaml()
            print(f"[IndustryStore] Initialized {self.industry} database")

    def _needs_sync(self) -> bool:
        """检查是否需要同步"""
        if not self.yaml_path.exists():
            return False

        # 检查数据库文件修改时间
        db_mtime = self.db_path.stat().st_mtime if self.db_path.exists() else 0

        # 检查 YAML 目录最新修改时间
        yaml_mtime = 0
        if self.yaml_path.exists():
            for f in self.yaml_path.rglob("*.yaml"):
                if not f.name.startswith("_"):
                    yaml_mtime = max(yaml_mtime, f.stat().st_mtime)

        return yaml_mtime > db_mtime

    def _sync_from_yaml(self):
        """从 YAML 同步到 SQLite"""
        start = time.time()

        conn = sqlite3.connect(str(self.db_path))

        # 创建表
        self._create_tables(conn)

        # 同步各层数据
        self._sync_indicators(conn)
        self._sync_scenarios(conn)
        self._sync_preferences(conn)

        # 更新同步元数据
        self._update_sync_meta(conn)

        conn.commit()
        conn.close()

        # 清除缓存
        self._cache.clear()

        print(f"[IndustryStore] Synced in {time.time() - start:.3f}s")

    def _create_tables(self, conn: sqlite3.Connection):
        """创建所有表"""
        # 语义层: 指标
        conn.execute("""
            CREATE TABLE IF NOT EXISTS indicators (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                industry TEXT,
                keywords TEXT,
                description TEXT,
                formula TEXT,
                unit TEXT,
                precision INTEGER,
                table_name TEXT,
                field_name TEXT,
                access_count INTEGER DEFAULT 0,
                importance REAL DEFAULT 0.5,
                updated TEXT,
                relations TEXT,
                _file_path TEXT
            )
        """)

        # 情景层: 场景
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scenarios (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                industry TEXT,
                keywords TEXT,
                description TEXT,
                required_indicators TEXT,
                optional_indicators TEXT,
                dimensions TEXT,
                template TEXT,
                usage_count INTEGER DEFAULT 0,
                satisfaction REAL DEFAULT 0.5,
                updated TEXT,
                _file_path TEXT
            )
        """)

        # 工作层: 偏好
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                default_industry TEXT,
                preferred_dimensions TEXT,
                default_time_range TEXT,
                preferred_format TEXT,
                frequent_queries TEXT,
                frequent_scenarios TEXT,
                updated TEXT
            )
        """)

        # 同步元数据
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (
                table_name TEXT PRIMARY KEY,
                last_sync TEXT,
                record_count INTEGER,
                file_hash TEXT
            )
        """)

        # 索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ind_code ON indicators(code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scn_code ON scenarios(code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prefs_user ON preferences(user_id)")

    # ==================== 同步方法 ====================

    def _sync_indicators(self, conn: sqlite3.Connection):
        """同步指标数据"""
        ind_dir = self.yaml_path / "indicators"
        if not ind_dir.exists():
            return

        conn.execute("DELETE FROM indicators")

        for f in ind_dir.glob("*.yaml"):
            if f.name.startswith("_"):
                continue

            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if not data:
                    continue

                conn.execute("""
                    INSERT INTO indicators (
                        id, code, name, industry, keywords, description,
                        formula, unit, precision, table_name, field_name,
                        access_count, importance, updated, relations, _file_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get("id"),
                    data.get("code"),
                    data.get("name"),
                    data.get("industry"),
                    json.dumps(data.get("keywords", [])),
                    data.get("description", ""),
                    data.get("definition", {}).get("formula"),
                    data.get("definition", {}).get("unit"),
                    data.get("definition", {}).get("precision"),
                    data.get("mapping", {}).get("table"),
                    data.get("mapping", {}).get("field"),
                    data.get("stats", {}).get("access_count", 0),
                    data.get("stats", {}).get("importance", 0.5),
                    data.get("stats", {}).get("updated", ""),
                    json.dumps(data.get("relations", {})),
                    str(f)
                ))
            except Exception as e:
                print(f"[IndustryStore] Warning: Failed to sync {f}: {e}")

    def _sync_scenarios(self, conn: sqlite3.Connection):
        """同步场景数据"""
        scn_dir = self.yaml_path / "scenarios"
        if not scn_dir.exists():
            # 创建空目录的占位记录
            return

        conn.execute("DELETE FROM scenarios")

        for f in scn_dir.glob("*.yaml"):
            if f.name.startswith("_"):
                continue

            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if not data:
                    continue

                conn.execute("""
                    INSERT INTO scenarios (
                        id, code, name, industry, keywords, description,
                        required_indicators, optional_indicators, dimensions,
                        template, usage_count, satisfaction, updated, _file_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get("id"),
                    data.get("code"),
                    data.get("name"),
                    data.get("industry"),
                    json.dumps(data.get("keywords", [])),
                    data.get("description", ""),
                    json.dumps(data.get("content", {}).get("required", [])),
                    json.dumps(data.get("content", {}).get("optional", [])),
                    json.dumps(data.get("content", {}).get("dimensions", {})),
                    json.dumps(data.get("template", {})),
                    data.get("stats", {}).get("usage_count", 0),
                    data.get("stats", {}).get("satisfaction", 0.5),
                    data.get("stats", {}).get("updated", ""),
                    str(f)
                ))
            except Exception as e:
                print(f"[IndustryStore] Warning: Failed to sync {f}: {e}")

    def _sync_preferences(self, conn: sqlite3.Connection):
        """同步用户偏好"""
        pref_file = self.yaml_path / "preferences.yaml"
        if not pref_file.exists():
            return

        try:
            data = yaml.safe_load(pref_file.read_text(encoding="utf-8"))
            if not data:
                return

            conn.execute("DELETE FROM preferences")

            conn.execute("""
                INSERT INTO preferences (
                    user_id, default_industry, preferred_dimensions,
                    default_time_range, preferred_format,
                    frequent_queries, frequent_scenarios, updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("user", "default"),
                data.get("preferences", {}).get("default_industry"),
                json.dumps(data.get("preferences", {}).get("preferred_dimensions", [])),
                data.get("preferences", {}).get("default_time_range"),
                data.get("preferences", {}).get("preferred_format"),
                json.dumps(data.get("frequent_queries", [])),
                json.dumps(data.get("frequent_scenarios", [])),
                data.get("updated", "")
            ))
        except Exception as e:
            print(f"[IndustryStore] Warning: Failed to sync preferences: {e}")

    def _update_sync_meta(self, conn: sqlite3.Connection):
        """更新同步元数据"""
        # 计算 YAML 文件 hash
        file_hash = self._calculate_yaml_hash()

        # 更新各表元数据
        for table in ["indicators", "scenarios", "preferences"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            conn.execute("""
                INSERT OR REPLACE INTO sync_meta
                (table_name, last_sync, record_count, file_hash)
                VALUES (?, datetime('now'), ?, ?)
            """, (table, count, file_hash))

    def _calculate_yaml_hash(self) -> str:
        """计算 YAML 文件 hash"""
        hashes = []
        if self.yaml_path.exists():
            for f in sorted(self.yaml_path.rglob("*.yaml")):
                if not f.name.startswith("_"):
                    content = f.read_bytes()
                    hashes.append(hashlib.md5(content).hexdigest())
        return hashlib.md5("".join(hashes).encode()).hexdigest() if hashes else ""

    # ==================== 检索接口 ====================

    def search(self, query: str, top_k: int = 5) -> Dict[str, List[Dict]]:
        """
        统一检索接口

        Args:
            query: 查询关键词
            top_k: 返回结果数量

        Returns:
            {
                "indicators": [...],
                "scenarios": [...],
                "query": query
            }
        """
        conn = sqlite3.connect(str(self.db_path))

        # 获取列名
        ind_columns = [desc[0] for desc in conn.execute("SELECT * FROM indicators LIMIT 1").description]
        scn_columns = [desc[0] for desc in conn.execute("SELECT * FROM scenarios LIMIT 1").description]

        # 搜索指标 (支持关键词搜索)
        indicators = conn.execute("""
            SELECT * FROM indicators
            WHERE keywords LIKE ? OR name LIKE ? OR description LIKE ?
            ORDER BY importance DESC, access_count DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", top_k)).fetchall()

        # 搜索场景
        scenarios = conn.execute("""
            SELECT * FROM scenarios
            WHERE keywords LIKE ? OR name LIKE ? OR description LIKE ?
            ORDER BY satisfaction DESC, usage_count DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", 3)).fetchall()

        conn.close()

        return {
            "indicators": [self._row_to_dict(row, ind_columns) for row in indicators],
            "scenarios": [self._row_to_dict(row, scn_columns) for row in scenarios],
            "query": query,
            "count": {
                "indicators": len(indicators),
                "scenarios": len(scenarios)
            }
        }

    def _row_to_dict(self, row: Any, columns: tuple = None) -> Dict:
        """将行数据转换为字典"""
        if not row:
            return {}

        # 如果是 tuple，使用列名映射
        if isinstance(row, tuple):
            if columns is None:
                return dict(row)
            return dict(zip(columns, row))

        # 如果是 sqlite3.Row
        result = dict(row)
        # 解析 JSON 字段
        for key in ["keywords", "relations", "required_indicators",
                    "optional_indicators", "dimensions", "template",
                    "preferred_dimensions", "frequent_queries", "frequent_scenarios"]:
            if key in result and result[key]:
                try:
                    result[key] = json.loads(result[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return result

    def get_indicator(self, code: str) -> Optional[Dict]:
        """获取单个指标"""
        conn = sqlite3.connect(str(self.db_path))
        columns = [desc[0] for desc in conn.execute("SELECT * FROM indicators LIMIT 1").description]
        row = conn.execute(
            "SELECT * FROM indicators WHERE code = ?", (code,)
        ).fetchone()
        conn.close()
        return self._row_to_dict(row, columns) if row else None

    def get_scenario(self, code: str) -> Optional[Dict]:
        """获取单个场景"""
        conn = sqlite3.connect(str(self.db_path))
        columns = [desc[0] for desc in conn.execute("SELECT * FROM scenarios LIMIT 1").description]
        row = conn.execute(
            "SELECT * FROM scenarios WHERE code = ?", (code,)
        ).fetchone()
        conn.close()
        return self._row_to_dict(row, columns) if row else None

    def get_preferences(self, user_id: str = "default") -> Optional[Dict]:
        """获取用户偏好"""
        conn = sqlite3.connect(str(self.db_path))
        columns = [desc[0] for desc in conn.execute("SELECT * FROM preferences LIMIT 1").description]
        row = conn.execute(
            "SELECT * FROM preferences WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return self._row_to_dict(row, columns) if row else None

    def get_all_indicators(self) -> List[Dict]:
        """获取所有指标"""
        conn = sqlite3.connect(str(self.db_path))
        columns = [desc[0] for desc in conn.execute("SELECT * FROM indicators LIMIT 1").description]
        rows = conn.execute("""
            SELECT * FROM indicators
            ORDER BY importance DESC, access_count DESC
        """).fetchall()
        conn.close()
        return [self._row_to_dict(row, columns) for row in rows]

    def get_all_scenarios(self) -> List[Dict]:
        """获取所有场景"""
        conn = sqlite3.connect(str(self.db_path))
        columns = [desc[0] for desc in conn.execute("SELECT * FROM scenarios LIMIT 1").description]
        rows = conn.execute("""
            SELECT * FROM scenarios
            ORDER BY satisfaction DESC, usage_count DESC
        """).fetchall()
        conn.close()
        return [self._row_to_dict(row, columns) for row in rows]

    # ==================== 写入接口 ====================

    def update_preferences(self, user_id: str, updates: Dict):
        """更新用户偏好"""
        conn = sqlite3.connect(str(self.db_path))

        # 获取现有记录
        existing = conn.execute(
            "SELECT * FROM preferences WHERE user_id = ?", (user_id,)
        ).fetchone()

        if existing:
            # 更新
            conn.execute("""
                UPDATE preferences SET
                    default_industry = COALESCE(?, default_industry),
                    preferred_dimensions = COALESCE(?, preferred_dimensions),
                    default_time_range = COALESCE(?, default_time_range),
                    preferred_format = COALESCE(?, preferred_format),
                    updated = datetime('now')
                WHERE user_id = ?
            """, (
                updates.get("default_industry"),
                json.dumps(updates.get("preferred_dimensions")) if updates.get("preferred_dimensions") else None,
                updates.get("default_time_range"),
                updates.get("preferred_format"),
                user_id
            ))
        else:
            # 插入
            conn.execute("""
                INSERT INTO preferences (user_id, default_industry, preferred_dimensions,
                    default_time_range, preferred_format, updated)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (
                user_id,
                updates.get("default_industry"),
                json.dumps(updates.get("preferred_dimensions", [])),
                updates.get("default_time_range"),
                updates.get("preferred_format")
            ))

        conn.commit()
        conn.close()

        # 同步回 YAML
        self._sync_to_yaml(user_id)

    def _sync_to_yaml(self, user_id: str):
        """将偏好同步回 YAML"""
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute(
            "SELECT * FROM preferences WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()

        if not row:
            return

        pref = self._row_to_dict(row, row.keys())

        # 构造 YAML 数据
        data = {
            "user": user_id,
            "preferences": {
                "default_industry": pref.get("default_industry"),
                "preferred_dimensions": pref.get("preferred_dimensions", []),
                "default_time_range": pref.get("default_time_range"),
                "preferred_format": pref.get("preferred_format")
            },
            "frequent_queries": pref.get("frequent_queries", []),
            "frequent_scenarios": pref.get("frequent_scenarios", []),
            "updated": datetime.now().strftime("%Y-%m-%d")
        }

        # 写入 YAML
        pref_file = self.yaml_path / "preferences.yaml"
        with open(pref_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def record_query(self, user_id: str, query: str):
        """记录用户查询 (用于推荐)"""
        conn = sqlite3.connect(str(self.db_path))

        # 获取现有历史
        existing = conn.execute(
            "SELECT frequent_queries FROM preferences WHERE user_id = ?", (user_id,)
        ).fetchone()

        history = json.loads(existing[0]) if existing and existing[0] else []

        # 更新计数
        found = False
        for h in history:
            if h.get("query") == query:
                h["count"] = h.get("count", 0) + 1
                found = True
                break

        if not found:
            history.append({"query": query, "count": 1})

        # 只保留 top 10
        history = sorted(history, key=lambda x: x["count"], reverse=True)[:10]

        conn.execute("""
            UPDATE preferences SET frequent_queries = ?, updated = datetime('now')
            WHERE user_id = ?
        """, (json.dumps(history), user_id))

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
            "preferences": conn.execute("SELECT COUNT(*) FROM preferences").fetchone()[0]
        }

        sync_meta = conn.execute("SELECT * FROM sync_meta").fetchall()
        stats["sync"] = []
        for m in sync_meta:
            stats["sync"].append({
                "table_name": m[0],
                "last_sync": m[1],
                "record_count": m[2],
                "file_hash": m[3]
            })

        conn.close()
        return stats

    def __repr__(self):
        return f"IndustryStore(industry='{self.industry}', db='{self.db_path}')"


# ==================== 便捷函数 ====================

def get_store(industry: str = "ecommerce", data_root: str = "data/industry") -> IndustryStore:
    """
    获取行业存储实例

    Args:
        industry: 行业名称
        data_root: 数据根目录

    Returns:
        IndustryStore 实例
    """
    return IndustryStore(industry, data_root)


# ==================== 测试 ====================

if __name__ == "__main__":
    import sys

    # 测试
    print("=" * 50)
    print("IndustryStore 测试")
    print("=" * 50)

    # 创建存储实例
    store = IndustryStore("ecommerce")

    # 获取统计
    print("\n1. 统计信息:")
    stats = store.get_stats()
    print(f"   指标数: {stats['indicators']}")
    print(f"   场景数: {stats['scenarios']}")

    # 搜索测试
    print("\n2. 搜索 '销售':")
    results = store.search("销售")
    print(f"   找到 {len(results['indicators'])} 个指标")
    for ind in results.get("indicators", []):
        print(f"   - {ind.get('name')} ({ind.get('code')})")

    print("\n3. 搜索 '趋势':")
    results = store.search("趋势")
    print(f"   找到 {len(results['scenarios'])} 个场景")
    for scn in results.get("scenarios", []):
        print(f"   - {scn.get('name')} ({scn.get('code')})")

    # 获取偏好
    print("\n4. 用户偏好:")
    prefs = store.get_preferences()
    if prefs:
        print(f"   默认行业: {prefs.get('default_industry')}")
        print(f"   常用维度: {prefs.get('preferred_dimensions')}")
        print(f"   时间范围: {prefs.get('default_time_range')}")

    # 获取单个指标
    print("\n5. 获取单个指标 'sales_amount':")
    ind = store.get_indicator("sales_amount")
    if ind:
        print(f"   名称: {ind.get('name')}")
        print(f"   公式: {ind.get('formula')}")
        print(f"   关键词: {ind.get('keywords')}")

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)
