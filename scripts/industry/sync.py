"""
dAnalyzer 行业数据同步模块

管理 YAML → SQLite 的双向同步逻辑。
由 IndustryStore 在初始化时按需调用，不直接使用。
"""

import sqlite3
import json
import yaml
import hashlib
import time
from pathlib import Path
from typing import List


def create_tables(conn: sqlite3.Connection):
    """创建所有 SQLite 表与索引"""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS indicators (
            id TEXT PRIMARY KEY, code TEXT NOT NULL, name TEXT NOT NULL,
            industry TEXT, keywords TEXT, description TEXT,
            formula TEXT, unit TEXT, precision INTEGER,
            table_name TEXT, field_name TEXT,
            access_count INTEGER DEFAULT 0, importance REAL DEFAULT 0.5,
            updated TEXT, relations TEXT, _file_path TEXT)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS scenarios (
            id TEXT PRIMARY KEY, code TEXT NOT NULL, name TEXT NOT NULL,
            industry TEXT, keywords TEXT, description TEXT,
            required_indicators TEXT, optional_indicators TEXT,
            dimensions TEXT, template TEXT,
            usage_count INTEGER DEFAULT 0, satisfaction REAL DEFAULT 0.5,
            updated TEXT, _file_path TEXT)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY, user_id TEXT NOT NULL UNIQUE,
            default_industry TEXT, preferred_dimensions TEXT,
            default_time_range TEXT, preferred_format TEXT,
            frequent_queries TEXT, frequent_scenarios TEXT, updated TEXT)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sync_meta (
            table_name TEXT PRIMARY KEY, last_sync TEXT,
            record_count INTEGER, file_hash TEXT)"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ind_code ON indicators(code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_scn_code ON scenarios(code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prefs_user ON preferences(user_id)")


def sync_indicators(conn: sqlite3.Connection, yaml_path: Path):
    """同步指标数据"""
    ind_dir = yaml_path / "indicators"
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
            conn.execute(
                """INSERT INTO indicators (
                    id, code, name, industry, keywords, description,
                    formula, unit, precision, table_name, field_name,
                    access_count, importance, updated, relations, _file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data.get("id"), data.get("code"), data.get("name"),
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
                    str(f),
                ),
            )
        except Exception as e:
            print(f"[IndustryStore] Warning: Failed to sync {f}: {e}")


def sync_scenarios(conn: sqlite3.Connection, yaml_path: Path):
    """同步场景数据"""
    scn_dir = yaml_path / "scenarios"
    if not scn_dir.exists():
        return

    conn.execute("DELETE FROM scenarios")
    for f in scn_dir.glob("*.yaml"):
        if f.name.startswith("_"):
            continue
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if not data:
                continue
            conn.execute(
                """INSERT INTO scenarios (
                    id, code, name, industry, keywords, description,
                    required_indicators, optional_indicators, dimensions,
                    template, usage_count, satisfaction, updated, _file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data.get("id"), data.get("code"), data.get("name"),
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
                    str(f),
                ),
            )
        except Exception as e:
            print(f"[IndustryStore] Warning: Failed to sync {f}: {e}")


def sync_preferences(conn: sqlite3.Connection, yaml_path: Path):
    """同步用户偏好"""
    pref_file = yaml_path / "preferences.yaml"
    if not pref_file.exists():
        return
    try:
        data = yaml.safe_load(pref_file.read_text(encoding="utf-8"))
        if not data:
            return
        conn.execute("DELETE FROM preferences")
        conn.execute(
            """INSERT INTO preferences (
                user_id, default_industry, preferred_dimensions,
                default_time_range, preferred_format,
                frequent_queries, frequent_scenarios, updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("user", "default"),
                data.get("preferences", {}).get("default_industry"),
                json.dumps(data.get("preferences", {}).get("preferred_dimensions", [])),
                data.get("preferences", {}).get("default_time_range"),
                data.get("preferences", {}).get("preferred_format"),
                json.dumps(data.get("frequent_queries", [])),
                json.dumps(data.get("frequent_scenarios", [])),
                data.get("updated", ""),
            ),
        )
    except Exception as e:
        print(f"[IndustryStore] Warning: Failed to sync preferences: {e}")


def calculate_yaml_hash(yaml_path: Path) -> str:
    """计算 YAML 目录的 md5 内容 hash"""
    hashes = []
    if yaml_path.exists():
        for f in sorted(yaml_path.rglob("*.yaml")):
            if not f.name.startswith("_"):
                hashes.append(hashlib.md5(f.read_bytes()).hexdigest())
    return hashlib.md5("".join(hashes).encode()).hexdigest() if hashes else ""


def update_sync_meta(conn: sqlite3.Connection, yaml_path: Path, tables: List[str]):
    """更新同步元数据"""
    file_hash = calculate_yaml_hash(yaml_path)
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        conn.execute(
            "INSERT OR REPLACE INTO sync_meta (table_name, last_sync, record_count, file_hash) "
            "VALUES (?, datetime('now'), ?, ?)",
            (table, count, file_hash),
        )


def sync_from_yaml(yaml_path: Path, db_path: Path, industry: str):
    """从 YAML 目录同步到 SQLite（完整同步）"""
    start = time.time()
    conn = sqlite3.connect(str(db_path))
    create_tables(conn)
    sync_indicators(conn, yaml_path)
    sync_scenarios(conn, yaml_path)
    sync_preferences(conn, yaml_path)
    update_sync_meta(conn, yaml_path, ["indicators", "scenarios", "preferences"])
    conn.commit()
    conn.close()
    elapsed = time.time() - start
    print(f"[IndustryStore] Synced {industry} in {elapsed:.3f}s")


def sync_preferences_to_yaml(db_path: Path, yaml_path: Path):
    """将偏好从 SQLite 写回 YAML"""
    import yaml

    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT * FROM preferences WHERE user_id = ?", ("default",)
    ).fetchone()
    conn.close()
    if not row:
        return

    cols = [desc[0] for desc in conn.execute("SELECT * FROM preferences LIMIT 1").description]
    pref = dict(zip(cols, row))

    data = {
        "user": "default",
        "preferences": {
            "default_industry": pref.get("default_industry"),
            "preferred_dimensions": json.loads(pref.get("preferred_dimensions", "[]")),
            "default_time_range": pref.get("default_time_range"),
            "preferred_format": pref.get("preferred_format"),
        },
        "frequent_queries": json.loads(pref.get("frequent_queries", "[]")),
        "frequent_scenarios": json.loads(pref.get("frequent_scenarios", "[]")),
        "updated": __import__("datetime").datetime.now().strftime("%Y-%m-%d"),
    }

    pref_file = yaml_path / "preferences.yaml"
    with open(pref_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
