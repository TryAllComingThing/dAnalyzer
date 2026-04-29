"""
dAnalyzer 数据查询执行脚本

用法:
    python scripts/execute_query.py --source csv --path data/sample.csv
    python scripts/execute_query.py --source excel --path data/sample.xlsx --sheet Sheet1
    python scripts/execute_query.py --source json --path data/sample.json
    python scripts/execute_query.py --source mysql --query "SELECT * FROM orders" --host localhost --user root

被 data-query SKILL.md 调用，统一数据查询入口。
"""

import argparse
import json
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

    Returns:
        {"success": true, "columns": [...], "rows": [[...], ...], "row_count": N}
    """
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
        return {"success": False, "error": str(e)}
    finally:
        connector.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="dAnalyzer 数据查询执行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--source", "-s", required=True,
                        choices=["csv", "json", "excel", "mysql", "clickhouse",
                                 "hive", "postgres", "python"],
                        help="数据源类型")
    parser.add_argument("--path", "-p",
                        help="文件路径 (file sources)")
    parser.add_argument("--query", "-q",
                        help="SQL查询语句 (database sources)")
    parser.add_argument("--output", "-o",
                        help="输出到文件")
    parser.add_argument("--sheet",
                        help="Excel 工作表名")

    # 数据库连接参数
    parser.add_argument("--host", help="数据库主机")
    parser.add_argument("--port", type=int, help="数据库端口")
    parser.add_argument("--user", "-u", help="数据库用户")
    parser.add_argument("--password", help="数据库密码")
    parser.add_argument("--database", "-d", help="数据库名")

    args = parser.parse_args()

    file_sources = {"csv", "json", "excel", "python"}
    db_sources = {"mysql", "clickhouse", "hive", "postgres"}

    if args.source in file_sources:
        if not args.path:
            print(json.dumps({"success": False, "error": "--path is required for file sources"}, ensure_ascii=False))
            sys.exit(1)
        kwargs = {}
        if args.sheet and args.source == "excel":
            kwargs["sheet_name"] = args.sheet
        result = execute_file_query(args.source, args.path, **kwargs)

    elif args.source in db_sources:
        if not args.query:
            print(json.dumps({"success": False, "error": "--query is required for database sources"}, ensure_ascii=False))
            sys.exit(1)
        config = {}
        if args.host:
            config["host"] = args.host
        if args.port:
            config["port"] = str(args.port)
        if args.user:
            config["user"] = args.user
        if args.password:
            config["password"] = args.password
        if args.database:
            config["database"] = args.database
        result = execute_db_query(args.source, args.query, config)
    else:
        result = {"success": False, "error": f"Unknown source: {args.source}"}

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
