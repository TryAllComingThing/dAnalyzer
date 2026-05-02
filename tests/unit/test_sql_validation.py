"""
SQL 两层校验测试 — 静态检查 + EXPLAIN + execute_db_query 校验链
"""
import json
import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestValidateSQLStatic:
    """validate_sql_static() — 无连接校验"""

    def test_empty_sql(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static("")
        assert r["valid"] is False
        assert r["error_type"] == "SQL_EMPTY"

    def test_none_sql(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static(None)
        assert r["valid"] is False
        assert r["error_type"] == "SQL_EMPTY"

    def test_not_select_show(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static("SHOW TABLES")
        assert r["valid"] is False

    def test_not_select_describe(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static("DESCRIBE orders")
        assert r["valid"] is False

    def test_forbidden_drop(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static("DROP TABLE orders")
        assert r["valid"] is False
        assert r["error_type"] == "SQL_NOT_SELECT"

    def test_forbidden_delete(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static("DELETE FROM orders WHERE id=1")
        assert r["valid"] is False

    def test_forbidden_insert(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static("INSERT INTO orders VALUES (1,2,3)")
        assert r["valid"] is False

    def test_forbidden_truncate(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static("TRUNCATE TABLE orders")
        assert r["valid"] is False

    def test_forbidden_in_subquery(self):
        """写操作关键字在子查询中也被拦截"""
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static("SELECT * FROM (DELETE FROM t) AS x")
        assert r["valid"] is False

    def test_unbalanced_parens_open(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static("SELECT a FROM (SELECT b FROM t")
        assert r["valid"] is False
        assert r["error_type"] == "SQL_SYNTAX_ERROR"
        assert "括号" in r["error"]

    def test_unbalanced_parens_close(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static("SELECT a FROM t)")
        assert r["valid"] is False
        assert r["error_type"] == "SQL_SYNTAX_ERROR"

    def test_valid_simple_select(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static("SELECT * FROM orders LIMIT 10")
        assert r is None  # None = 通过

    def test_valid_complex_select(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static(
            "SELECT d.dept_name, COUNT(*) AS cnt "
            "FROM sys_user u "
            "JOIN sys_dept d ON u.dept_id = d.dept_id "
            "WHERE u.status = '0' "
            "GROUP BY d.dept_name "
            "HAVING cnt > 0 "
            "ORDER BY cnt DESC"
        )
        assert r is None

    def test_valid_with_subquery(self):
        from scripts.execute_query import validate_sql_static
        r = validate_sql_static(
            "SELECT * FROM (SELECT dept_id, COUNT(*) AS n FROM sys_user GROUP BY dept_id) AS t WHERE n > 0"
        )
        assert r is None


class TestValidateSQLExplain:
    """validate_sql_explain() — EXPLAIN 校验（需要本地 MySQL）"""

    MYSQL_CONFIG = {
        "host": "localhost",
        "port": "3306",
        "user": "root",
        "password": os.environ.get("MYSQL_PASS", ""),
        "database": "ry",
    }

    def test_explain_valid_sql(self):
        from scripts.execute_query import validate_sql_explain
        r = validate_sql_explain("mysql", "SELECT COUNT(*) FROM sys_dept", self.MYSQL_CONFIG)
        assert r is None  # None = 通过

    def test_explain_table_not_found(self):
        from scripts.execute_query import validate_sql_explain
        r = validate_sql_explain("mysql", "SELECT * FROM table_does_not_exist_xyz", self.MYSQL_CONFIG)
        assert r is not None
        assert r["error_type"] in ("SQL_TABLE_NOT_FOUND", "SQL_EXECUTION_ERROR")

    def test_explain_syntax_error(self):
        from scripts.execute_query import validate_sql_explain
        r = validate_sql_explain("mysql", "SELEC * FORM sys_dept", self.MYSQL_CONFIG)
        assert r is not None
        assert r["error_type"] in ("SQL_SYNTAX_ERROR", "SQL_EXECUTION_ERROR")

    def test_explain_missing_config(self):
        from scripts.execute_query import validate_sql_explain
        r = validate_sql_explain("mysql", "SELECT 1", {})
        assert r is not None
        assert r["error_type"] == "CONNECTION_CONFIG_ERROR"


class TestExecuteDBQueryValidation:
    """execute_db_query() — 完整校验→执行链"""

    def test_validation_chain_rejects_bad_sql(self):
        """校验链应在执行前拦截语法错误"""
        from scripts.execute_query import execute_db_query
        config = {
            "host": "localhost", "port": "3306", "user": "root",
            "password": os.environ.get("MYSQL_PASS", ""), "database": "ry",
        }
        # SQL 语法错误: SELEC→SELECT, FORM→FROM
        result = execute_db_query("mysql", "SELEC * FR OM sys_dept", config)
        assert result.get("valid") is False or result.get("success") is False
        assert "error_type" in result
        assert "suggestion" in result

    def test_validation_chain_passes_valid_sql(self):
        """校验链通过后正常返回数据"""
        from scripts.execute_query import execute_db_query
        config = {
            "host": "localhost", "port": "3306", "user": "root",
            "password": os.environ.get("MYSQL_PASS", ""), "database": "ry",
        }
        result = execute_db_query("mysql", "SELECT COUNT(*) AS cnt FROM sys_dept", config)
        assert result["success"] is True
        assert result["row_count"] > 0
        assert "columns" in result
        assert "execution_time_ms" in result


class TestValidateOnlyCLI:
    """--validate-only CLI"""

    ENV = {**os.environ, "PYTHONWARNINGS": "ignore"}

    def _run_validate(self, sql):
        result = subprocess.run(
            [sys.executable, "scripts/execute_query.py", "--source", "mysql",
             "--query", sql, "--validate-only",
             "--host", "localhost", "--port", "3306", "--user", "root",
             "--password", os.environ.get("MYSQL_PASS", ""),
             "--database", "ry"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30,
            env=self.ENV,
        )
        # validate-only 输出 compact JSON（单行），但也支持多行
        start = result.stdout.find("{")
        if start == -1:
            return {}
        depth = 0
        for i, ch in enumerate(result.stdout[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(result.stdout[start:i + 1])
                    except json.JSONDecodeError:
                        return {}
        return {}

    def test_validate_only_valid(self):
        data = self._run_validate("SELECT COUNT(*) FROM sys_dept")
        assert data.get("valid") is True

    def test_validate_only_bad_table(self):
        data = self._run_validate("SELECT * FROM not_a_table")
        assert data["valid"] is False
        assert data["error_type"] in ("SQL_TABLE_NOT_FOUND", "SQL_EXECUTION_ERROR")
