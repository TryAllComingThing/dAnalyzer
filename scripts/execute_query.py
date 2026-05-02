"""
dAnalyzer 数据查询执行脚本

用法:
    # 按数据源名称查询（推荐）
    python scripts/execute_query.py --datasource fmcg_orders --query "SELECT * FROM orders LIMIT 10"

    # 文件数据源
    python scripts/execute_query.py --datasource test_orders
    python scripts/execute_query.py --source csv --path knowledge/sample.csv

    # 数据库直接连接
    python scripts/execute_query.py --source mysql --query "SELECT * FROM orders" --host localhost --user root

被 data-query SKILL.md 调用，统一数据查询入口。
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

# 确保项目根目录在 sys.path 中
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from connectors.tool.base import create_tool_connector
from connectors.datawarehouse.base import create_connector


# ── SQL 安全规则 ──────────────────────────────────────────────

FORBIDDEN_SQL = re.compile(
    r'\b(DROP|DELETE|TRUNCATE|ALTER|CREATE|INSERT|UPDATE|GRANT|REVOKE)\b',
    re.IGNORECASE,
)

# 常见 SQL 语法错误模式
SYNTAX_SMELLS = [
    (re.compile(r'FROM\s*,', re.IGNORECASE), "FROM 后多逗号"),
    (re.compile(r'WHERE\s*,', re.IGNORECASE), "WHERE 后多逗号"),
    (re.compile(r'SELECT\s*,', re.IGNORECASE), "SELECT 后多逗号"),
    (re.compile(r'\(\s*,', re.IGNORECASE), "左括号后多逗号"),
    (re.compile(r',\s*\)', re.IGNORECASE), "右括号前多逗号"),
    (re.compile(r'GROUP\s+BY\s*$', re.IGNORECASE), "GROUP BY 后无字段"),
    (re.compile(r'ORDER\s+BY\s*$', re.IGNORECASE), "ORDER BY 后无字段"),
]


def validate_sql_static(sql: str) -> dict | None:
    """
    静态 SQL 校验（无需数据库连接）。返回 None = 通过，返回 dict = 失败。

    Returns:
        None 或 {"valid": false, "error_type": "...", "error": "...", "suggestion": "..."}
    """
    if not sql or not sql.strip():
        return {
            "valid": False, "error_type": "SQL_EMPTY",
            "error": "SQL 语句为空",
            "suggestion": "提供有效的 SELECT 查询语句",
        }

    # 检查是否有基本 SQL 结构
    if not re.search(r'\bSELECT\b', sql, re.IGNORECASE):
        return {
            "valid": False, "error_type": "SQL_NOT_SELECT",
            "error": "SQL 语句不是 SELECT 查询",
            "suggestion": "仅支持 SELECT 查询",
        }

    # 检查禁止的写操作
    m = FORBIDDEN_SQL.search(sql)
    if m:
        return {
            "valid": False, "error_type": "SQL_FORBIDDEN",
            "error": f"SQL 包含禁止操作: {m.group(0)}",
            "suggestion": "只允许只读 SELECT 查询，移除写操作关键字",
        }

    # 检查常见的语法问题
    for pattern, desc in SYNTAX_SMELLS:
        if pattern.search(sql):
            return {
                "valid": False, "error_type": "SQL_SYNTAX_ERROR",
                "error": f"疑似语法错误: {desc}",
                "suggestion": "检查逗号位置，确保语法正确",
            }

    # 检查括号是否平衡
    if sql.count("(") != sql.count(")"):
        return {
            "valid": False, "error_type": "SQL_SYNTAX_ERROR",
            "error": "括号不匹配",
            "suggestion": f"左括号 {sql.count('(')} 个，右括号 {sql.count(')')} 个，请检查",
        }

    return None


def validate_sql_explain(source: str, sql: str, config: dict) -> dict | None:
    """
    通过 EXPLAIN 验证 SQL 语法（需连接数据库）。返回 None = 通过，返回 dict = 失败。
    """
    # 构建 EXPLAIN 语句
    explain_sql = f"EXPLAIN {sql}"
    connector = None
    try:
        connector = create_connector(source, config)
        connector.connect()
        connector.execute(explain_sql)
        return None
    except Exception as e:
        err_msg = str(e).lower()
        # 分类错误类型（按优先级匹配）
        if any(kw in err_msg for kw in ("missing required config", "config")):
            error_type = "CONNECTION_CONFIG_ERROR"
            suggestion = "数据库连接配置不完整，用 --datasource <name> 指定已注册的数据源，或通过 --host/--port/--user 提供完整连接参数。"
        elif any(kw in err_msg for kw in ("syntax", "parse", "parsing", "malformed")):
            error_type = "SQL_SYNTAX_ERROR"
            suggestion = "SQL 语法错误，请检查关键字拼写、引号配对、从句顺序。基于 datasource 的 schema_hint 重新生成。"
        elif any(kw in err_msg for kw in ("table", "relation", "doesn't exist", "does not exist", "not found")):
            error_type = "SQL_TABLE_NOT_FOUND"
            suggestion = "表名不存在，请用 --datasource <name> --schema 获取正确的表名和列名后重新生成。"
        elif any(kw in err_msg for kw in ("column", "field", "unknown column", "attribute")):
            error_type = "SQL_COLUMN_NOT_FOUND"
            suggestion = "列名不存在，请用 --datasource <name> --schema 获取正确的列名后重新生成。"
        elif any(kw in err_msg for kw in ("connection", "refused", "timeout", "network", "access denied")):
            error_type = "CONNECTION_ERROR"
            suggestion = "数据库连接失败，检查连接配置和网络后重试。"
        else:
            error_type = "SQL_EXECUTION_ERROR"
            suggestion = "SQL 执行错误，检查语句逻辑后重试。"
        return {
            "valid": False, "error_type": error_type,
            "error": str(e)[:300],
            "suggestion": suggestion,
        }
    finally:
        if connector:
            try:
                connector.disconnect()
            except Exception:
                pass


# ── 数据源注册表 ──────────────────────────────────────────────

def _load_datasources():
    """加载 datasources.yaml 注册表"""
    try:
        import yaml
    except ImportError:
        import json as _json
        # 无 PyYAML 时回退，不影响直接 --source 模式
        return {"databases": [], "files": [], "file_discovery": {}}

    path = _project_root / "connectors" / "datasources.yaml"
    if not path.exists():
        return {"databases": [], "files": [], "file_discovery": {}}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {"databases": [], "files": [], "file_discovery": {}}


def _resolve_env(value: str) -> str:
    """解析 ${ENV_VAR:default} 格式的环境变量引用"""
    if not isinstance(value, str):
        return str(value)

    def _replace(m):
        var_name = m.group(1)
        default = m.group(2) if m.group(2) is not None else ""
        return os.environ.get(var_name, default)
    return re.sub(r'\$\{(\w+)(?::([^}]*))?\}', _replace, value)


def resolve_datasource(name: str):
    """按名称查找数据源，返回 (source_type, kwargs) 供 execute_file_query/execute_db_query 使用"""
    registry = _load_datasources()

    # 搜索 databases
    for db in registry.get("databases", []):
        if db["name"] == name:
            config = {k: _resolve_env(v) for k, v in db.get("config", {}).items()}
            defaults = db.get("defaults", {})
            return "db", {
                "source": db["type"],
                "config": config,
                "defaults": defaults,
                "description": db.get("description", ""),
            }

    # 搜索 files
    for f in registry.get("files", []):
        if f["name"] == name:
            path = _project_root / f["path"]
            return "file", {
                "source": f["type"],
                "path": str(path),
                "description": f.get("description", ""),
            }

    # 运行时文件发现：按扩展名查找
    discovery = registry.get("file_discovery", {})
    search_paths = discovery.get("search_paths", ["."])
    ext_map = discovery.get("extensions", {})

    # 检查 name 是否是一个存在的文件路径
    candidate = Path(name)
    if candidate.exists():
        ext = candidate.suffix.lstrip(".")
        source = ext_map.get(ext, ext)
        return "file", {"source": source, "path": str(candidate)}

    # 在 search_paths 中查找
    for sp in search_paths:
        base = _project_root / sp if not Path(sp).is_absolute() else Path(sp)
        if not base.exists():
            continue
        for ext in ext_map:
            target = base / f"{name}.{ext}"
            if target.exists():
                source = ext_map[ext]
                return "file", {"source": source, "path": str(target)}

    return None, {"error": f"数据源 '{name}' 未在 datasources.yaml 中注册，且未在搜索路径中找到同名文件"}


# ── 查询执行 ──────────────────────────────────────────────────

def execute_file_query(source: str, file_path: str, **kwargs) -> dict:
    """
    执行文件源查询 (CSV/JSON/Excel)

    Returns:
        {"success": true, "columns": [...], "rows": [[...], ...], "row_count": N}
    """
    connector = create_tool_connector(source)
    result = connector.read(file_path, **kwargs)
    if not result.success:
        return {"success": False, "error": result.error}

    return {
        "success": True,
        "columns": result.columns,
        "row_count": result.row_count,
        "raw_data": result.raw_data,
        "file_path": file_path,
    }


def execute_db_query(source: str, sql: str, config: dict) -> dict:
    """
    执行数据库查询 (MySQL/ClickHouse/Hive/PostgreSQL)
    执行前进行 SQL 校验: 静态检查 → EXPLAIN 语法验证 → 执行

    Returns:
        {"success": true, ...} 或 {"success": false, "error_type": "...", "error": "...", "suggestion": "..."}
    """
    # ── 1. 静态校验 ──
    static_err = validate_sql_static(sql)
    if static_err:
        return static_err

    # ── 2. EXPLAIN 语法验证 ──
    explain_err = validate_sql_explain(source, sql, config)
    if explain_err:
        return explain_err

    # ── 3. 正式执行 ──
    start = time.time()
    connector = create_connector(source, config)
    try:
        query_result = connector.execute(sql)
        elapsed = (time.time() - start) * 1000

        return {
            "success": True,
            "columns": query_result.columns,
            "rows": query_result.rows,
            "row_count": query_result.row_count,
            "execution_time_ms": round(elapsed, 2),
        }
    except Exception as e:
        return {
            "success": False,
            "error_type": "SQL_EXECUTION_ERROR",
            "error": str(e)[:300],
            "suggestion": "SQL 语法正确但执行时出错，检查查询逻辑和数据类型。",
        }
    finally:
        connector.disconnect()


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="dAnalyzer 数据查询执行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # 数据源指定方式（二选一）
    parser.add_argument("--datasource", "-d",
                        help="数据源名称（从 connectors/datasources.yaml 注册表查找）")
    parser.add_argument("--source", "-s",
                        choices=["csv", "json", "excel", "mysql", "clickhouse",
                                 "hive", "postgres", "python"],
                        help="数据源类型（直接指定，不查注册表）")

    parser.add_argument("--path", "-p", help="文件路径 (file sources)")
    parser.add_argument("--query", "-q", help="SQL查询语句 (database sources)")
    parser.add_argument("--output", "-o", help="输出到文件")
    parser.add_argument("--sheet", help="Excel 工作表名")
    parser.add_argument("--schema", action="store_true",
                        help="输出数据源的 schema_hint（表名+列名），不执行查询")
    parser.add_argument("--validate-only", action="store_true",
                        help="仅校验 SQL 语法（静态检查 + EXPLAIN），不执行查询")

    # 数据库连接参数（--source 直接模式使用）
    parser.add_argument("--host", help="数据库主机")
    parser.add_argument("--port", type=int, help="数据库端口")
    parser.add_argument("--user", "-u", help="数据库用户")
    parser.add_argument("--password", help="数据库密码")
    parser.add_argument("--database", help="数据库名")

    args = parser.parse_args()

    # ── 解析数据源 ──
    source = args.source
    file_path = args.path
    sql = args.query
    db_config = {}

    if args.datasource:
        if args.source:
            print(json.dumps({"success": False, "error": "--datasource 和 --source 不能同时使用"}, ensure_ascii=False))
            sys.exit(1)

        ds_type, ds_info = resolve_datasource(args.datasource)

        if ds_type is None:
            print(json.dumps({"success": False, "error": ds_info["error"]}, ensure_ascii=False))
            sys.exit(1)

        if ds_type == "file":
            source = ds_info["source"]
            file_path = args.path or ds_info["path"]
        elif ds_type == "db":
            source = ds_info["source"]
            db_config = ds_info.get("config", {})
            defaults = ds_info.get("defaults", {})
            # 合并默认值（CLI 参数可覆盖）
            if not sql:
                sql = args.query
            if args.host:
                db_config["host"] = args.host
            if args.port:
                db_config["port"] = str(args.port)
            if args.user:
                db_config["user"] = args.user
            if args.password:
                db_config["password"] = args.password
            if args.database:
                db_config["database"] = args.database
    else:
        # 直接 --source 模式（向后兼容）
        if args.host:
            db_config["host"] = args.host
        if args.port:
            db_config["port"] = str(args.port)
        if args.user:
            db_config["user"] = args.user
        if args.password:
            db_config["password"] = args.password
        if args.database:
            db_config["database"] = args.database

    # ── 执行 ──
    file_sources = {"csv", "json", "excel", "python"}
    db_sources = {"mysql", "clickhouse", "hive", "postgres"}

    # --schema: 输出数据源 schema_hint
    if args.schema:
        if not args.datasource:
            print(json.dumps({"success": False, "error": "--schema 需要配合 --datasource 使用"}, ensure_ascii=False))
            sys.exit(1)
        ds_type, ds_info = resolve_datasource(args.datasource)
        if ds_type is None:
            print(json.dumps({"success": False, "error": ds_info["error"]}, ensure_ascii=False))
            sys.exit(1)
        schema_data = {"success": True, "datasource": args.datasource}
        # 数据库: 输出 schema_hint
        registry = _load_datasources()
        for db in registry.get("databases", []):
            if db["name"] == args.datasource:
                schema_data["type"] = "database"
                schema_data["db_type"] = db["type"]
                schema_data["tables"] = db.get("schema_hint", {}).get("tables", [])
                break
        for f in registry.get("files", []):
            if f["name"] == args.datasource:
                schema_data["type"] = "file"
                schema_data["file_type"] = f["type"]
                schema_data["columns"] = f.get("schema_hint", {}).get("columns", [])
                break
        print(json.dumps(schema_data, ensure_ascii=False, indent=2))
        return

    # --validate-only: 仅校验 SQL
    if args.validate_only:
        if not sql:
            print(json.dumps({"success": False, "error": "--validate-only 需要 --query"}, ensure_ascii=False))
            sys.exit(1)
        if source not in db_sources:
            print(json.dumps({"success": False, "error": "--validate-only 仅支持数据库数据源"}, ensure_ascii=False))
            sys.exit(1)
        static_err = validate_sql_static(sql)
        if static_err:
            print(json.dumps(static_err, ensure_ascii=False))
            return
        explain_err = validate_sql_explain(source, sql, db_config)
        if explain_err:
            print(json.dumps(explain_err, ensure_ascii=False))
            return
        print(json.dumps({"valid": True, "message": "SQL 语法校验通过"}, ensure_ascii=False))
        return

    if source in file_sources:
        if not file_path:
            print(json.dumps({"success": False, "error": "--path is required for file sources"}, ensure_ascii=False))
            sys.exit(1)
        kwargs = {}
        if args.sheet and source == "excel":
            kwargs["sheet_name"] = args.sheet
        result = execute_file_query(source, file_path, **kwargs)

    elif source in db_sources:
        if not sql:
            print(json.dumps({"success": False, "error": "--query is required for database sources"}, ensure_ascii=False))
            sys.exit(1)
        result = execute_db_query(source, sql, db_config)
    else:
        result = {"success": False, "error": f"Unknown source: {source}"}

    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"[QueryExecutor] Results written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
