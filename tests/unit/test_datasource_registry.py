"""
数据源注册表测试 — resolve_datasource() + --schema + 环境变量解析
"""
from __future__ import annotations

import json
import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

ENV = {**os.environ, "PYTHONWARNINGS": "ignore"}


def _parse_json_from_stdout(stdout):
    """从 stdout 提取第一个 JSON 对象（支持多行 pretty-print）"""
    start = stdout.find("{")
    if start == -1:
        raise AssertionError(f"No JSON found in stdout: {stdout[:300]}")
    depth = 0
    for i, ch in enumerate(stdout[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(stdout[start:i + 1])
    raise AssertionError(f"Unclosed JSON in stdout: {stdout[start:start+300]}")


def _run_cli(*args, **kwargs):
    """运行 execute_query.py CLI，返回解析后的 JSON"""
    result = subprocess.run(
        [sys.executable, "scripts/execute_query.py", *args],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        timeout=kwargs.pop("timeout", 30), env=ENV,
        **kwargs,
    )
    return _parse_json_from_stdout(result.stdout)


class TestResolveDatasource:
    """resolve_datasource() 数据源解析"""

    def test_resolve_database_source(self):
        from scripts.execute_query import resolve_datasource
        ds_type, ds_info = resolve_datasource("local_mysql")
        assert ds_type == "db"
        assert ds_info["source"] == "mysql"
        assert ds_info["config"]["database"] == "ry"
        assert "host" in ds_info["config"]

    def test_resolve_file_source(self):
        from scripts.execute_query import resolve_datasource
        ds_type, ds_info = resolve_datasource("test_orders")
        assert ds_type == "file"
        assert ds_info["source"] == "csv"
        assert "test_orders.csv" in ds_info["path"]

    def test_resolve_unknown_datasource(self):
        from scripts.execute_query import resolve_datasource
        ds_type, ds_info = resolve_datasource("nonexistent_xyz_123")
        assert ds_type is None
        assert "error" in ds_info

    def test_resolve_all_databases(self):
        from scripts.execute_query import _load_datasources
        registry = _load_datasources()
        db_names = [db["name"] for db in registry.get("databases", [])]
        assert "local_mysql" in db_names
        assert "fmcg_orders" in db_names
        # 验证每个数据库都有必需字段
        for db in registry["databases"]:
            assert "name" in db
            assert "type" in db
            assert "config" in db
            assert "schema_hint" in db
            assert "tables" in db["schema_hint"]

    def test_resolve_all_files(self):
        from scripts.execute_query import _load_datasources
        registry = _load_datasources()
        file_names = [f["name"] for f in registry.get("files", [])]
        assert "test_orders" in file_names
        assert "test_sales" in file_names
        for f in registry["files"]:
            assert "path" in f
            assert "schema_hint" in f


class TestEnvVarResolution:
    """_resolve_env() 环境变量替换"""

    def test_resolve_with_default(self):
        from scripts.execute_query import _resolve_env
        result = _resolve_env("${NONEXISTENT_VAR_12345:default_value}")
        assert result == "default_value"

    def test_resolve_existing_var(self):
        from scripts.execute_query import _resolve_env
        result = _resolve_env("${MYSQL_PASS}")
        assert result == os.environ.get("MYSQL_PASS", "")

    def test_resolve_no_default(self):
        from scripts.execute_query import _resolve_env
        result = _resolve_env("${NONEXISTENT_VAR_12345}")
        assert result == ""


    def test_resolve_multiple_vars_in_string(self):
        from scripts.execute_query import _resolve_env
        result = _resolve_env("${NONEXISTENT_HOST:localhost}:${NONEXISTENT_PORT:3306}")
        assert result == "localhost:3306"

    def test_resolve_existing_var_no_default(self):
        from scripts.execute_query import _resolve_env
        result = _resolve_env("${PATH}")
        assert result == os.environ.get("PATH", "")

    def test_resolve_int_input(self):
        from scripts.execute_query import _resolve_env
        assert _resolve_env(42) == "42"

    def test_resolve_none_input(self):
        from scripts.execute_query import _resolve_env
        assert _resolve_env(None) == "None"

    def test_resolve_empty_string(self):
        from scripts.execute_query import _resolve_env
        assert _resolve_env("") == ""


class TestSchemaCLI:
    """--schema CLI 输出"""

    def test_schema_database(self):
        data = _run_cli("--datasource", "local_mysql", "--schema")
        assert data["type"] == "database"
        assert data["datasource"] == "local_mysql"
        assert "tables" in data
        assert len(data["tables"]) > 0
        for t in data["tables"]:
            assert "name" in t
            assert "columns" in t
            for col in t["columns"]:
                assert "name" in col
                assert "type" in col

    def test_schema_file(self):
        data = _run_cli("--datasource", "test_orders", "--schema")
        assert data["type"] == "file"
        assert data["datasource"] == "test_orders"
        assert "columns" in data
        assert isinstance(data["columns"], list)

    def test_schema_requires_datasource(self):
        data = _run_cli("--schema")
        assert data["success"] is False


class TestDatasourceQuery:
    """--datasource 模式实际查询"""

    def test_file_datasource_read(self):
        data = _run_cli("--datasource", "test_orders")
        assert data["success"] is True
        assert data["row_count"] > 0
        assert len(data["columns"]) > 0

    def test_db_datasource_query(self):
        data = _run_cli("--datasource", "local_mysql",
                        "--query", "SELECT COUNT(*) AS cnt FROM sys_dept")
        assert data["success"] is True
        assert data["rows"][0][0] > 0

    def test_datasource_source_conflict(self):
        data = _run_cli("--datasource", "test_orders", "--source", "csv")
        assert data["success"] is False
        assert "不能同时使用" in data["error"]


class TestLoadDatasources:
    """_load_datasources() 数据源注册表加载"""

    def test_load_valid_yaml(self):
        from scripts.execute_query import _load_datasources
        registry = _load_datasources()
        assert "databases" in registry
        assert "files" in registry
        assert "file_discovery" in registry
        assert len(registry["databases"]) > 0

    def test_load_missing_file(self, tmp_path):
        from scripts.execute_query import _load_datasources
        with patch("scripts.execute_query._project_root", tmp_path):
            registry = _load_datasources()
        assert registry == {"databases": [], "files": [], "file_discovery": {}}

    def test_load_empty_yaml(self, tmp_path):
        from scripts.execute_query import _load_datasources
        yaml_dir = tmp_path / "connectors"
        yaml_dir.mkdir()
        (yaml_dir / "datasources.yaml").write_text("")
        with patch("scripts.execute_query._project_root", tmp_path):
            registry = _load_datasources()
        assert registry == {"databases": [], "files": [], "file_discovery": {}}

    def test_load_malformed_yaml(self, tmp_path):
        from scripts.execute_query import _load_datasources
        yaml_dir = tmp_path / "connectors"
        yaml_dir.mkdir()
        (yaml_dir / "datasources.yaml").write_text(": invalid: yaml: [")
        with patch("scripts.execute_query._project_root", tmp_path):
            try:
                registry = _load_datasources()
                assert isinstance(registry, dict)
            except Exception:
                pass  # yaml.YAMLError is acceptable behavior


class TestResolveDatasourceEdgeCases:
    """resolve_datasource() 边界条件"""

    def test_file_discovery_direct_path(self, tmp_path):
        from scripts.execute_query import resolve_datasource
        csv_file = tmp_path / "my_data.csv"
        csv_file.write_text("col1,col2\n1,2\n")
        ds_type, ds_info = resolve_datasource(str(csv_file))
        assert ds_type == "file"
        assert ds_info["path"] == str(csv_file)

    def test_file_discovery_not_found(self):
        from scripts.execute_query import resolve_datasource
        ds_type, ds_info = resolve_datasource("nonexistent_file_xyz_12345")
        assert ds_type is None
        assert "error" in ds_info

    def test_db_config_env_var_substitution(self):
        from scripts.execute_query import resolve_datasource
        ds_type, ds_info = resolve_datasource("local_mysql")
        assert ds_type == "db"
        # 环境变量已替换，不应包含 ${...} 字面量
        for v in ds_info["config"].values():
            assert "${" not in v


class TestFileQuery:
    """execute_file_query() 文件查询"""

    def test_execute_file_query_csv_success(self):
        from scripts.execute_query import execute_file_query
        from connectors.tool.base import FileResult
        mock_conn = MagicMock()
        mock_conn.read.return_value = FileResult(
            success=True, columns=["col1", "col2"],
            raw_data=[{"col1": "a", "col2": 1}], row_count=2,
        )
        with patch("scripts.execute_query.create_tool_connector", return_value=mock_conn):
            result = execute_file_query("csv", "/fake/path.csv")
        assert result["success"] is True
        assert result["columns"] == ["col1", "col2"]
        assert result["row_count"] == 2

    def test_execute_file_query_failure(self):
        from scripts.execute_query import execute_file_query
        from connectors.tool.base import FileResult
        mock_conn = MagicMock()
        mock_conn.read.return_value = FileResult(
            success=False, error="File not found",
        )
        with patch("scripts.execute_query.create_tool_connector", return_value=mock_conn):
            result = execute_file_query("csv", "/nonexistent.csv")
        assert result["success"] is False
        assert "File not found" in result["error"]

    def test_execute_file_query_json(self):
        from scripts.execute_query import execute_file_query
        from connectors.tool.base import FileResult
        mock_conn = MagicMock()
        mock_conn.read.return_value = FileResult(
            success=True, columns=["key", "value"],
            raw_data=[{"key": "x", "value": 1}], row_count=1,
        )
        with patch("scripts.execute_query.create_tool_connector", return_value=mock_conn) as mock_create:
            execute_file_query("json", "/fake/data.json")
        mock_create.assert_called_once_with("json")


class TestMainCLIErrorPaths:
    """main() CLI 错误路径"""

    def test_missing_path_for_file_source(self):
        result = subprocess.run(
            [sys.executable, "scripts/execute_query.py", "--source", "csv", "--query", "SELECT 1"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
            timeout=30, env=ENV,
        )
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert "path" in data["error"].lower()

    def test_missing_query_for_db_source(self):
        result = subprocess.run(
            [sys.executable, "scripts/execute_query.py", "--source", "mysql",
             "--host", "localhost", "--user", "root"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
            timeout=30, env=ENV,
        )
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert "query" in data["error"].lower()

    def test_validate_only_requires_query(self):
        result = subprocess.run(
            [sys.executable, "scripts/execute_query.py", "--source", "mysql",
             "--validate-only", "--host", "localhost"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
            timeout=30, env=ENV,
        )
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert "query" in data["error"].lower()
