# -*- coding: utf-8 -*-
"""
数据库连接器集成测试

测试所有 5 种数据库连接器:
  - MySQL (pymysql)
  - ClickHouse (clickhouse-driver)
  - PostgreSQL (psycopg2)
  - Hive (pyhive)
  - Oracle (oracledb)

使用 mock 模拟数据库驱动层，在不依赖真实数据库的前提下验证连接器逻辑。
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from connectors import create_connector
from connectors.datawarehouse.base import QueryResult


# ==================== Fixtures ====================

@pytest.fixture
def mock_cursor():
    """通用 mock cursor"""
    cursor = MagicMock()
    cursor.description = [
        ("id",), ("name",), ("amount",), ("created_at",)
    ]
    cursor.fetchmany.return_value = [
        (1, "Alice", 100.0, "2024-01-01"),
        (2, "Bob", 200.0, "2024-01-02"),
    ]
    return cursor


@pytest.fixture
def mysql_config():
    return {"host": "localhost", "port": 3306, "database": "test",
            "user": "root", "password": "secret"}


@pytest.fixture
def ch_config():
    return {"host": "localhost", "port": 9000, "database": "default",
            "user": "default", "password": "secret"}


@pytest.fixture
def pg_config():
    return {"host": "localhost", "port": 5432, "database": "test",
            "user": "postgres", "password": "secret"}


@pytest.fixture
def hive_config():
    return {"host": "localhost", "port": 10000, "database": "default"}


@pytest.fixture
def oracle_config():
    return {"host": "localhost", "port": 1521, "service": "ORCL",
            "user": "system", "password": "oracle"}


# ==================== QueryResult 测试 ====================

class TestQueryResult:
    """QueryResult 数据结构测试"""

    def test_basic(self):
        r = QueryResult(
            columns=["a", "b"],
            rows=[(1, 2), (3, 4)],
            row_count=2,
            execution_time_ms=5.0,
        )
        assert r.columns == ["a", "b"]
        assert r.row_count == 2
        assert r.execution_time_ms == 5.0

    def test_to_csv(self, tmp_path):
        r = QueryResult(
            columns=["id", "val"],
            rows=[(1, "x"), (2, "y")],
            row_count=2,
            execution_time_ms=1.0,
        )
        out = tmp_path / "test.csv"
        path = r.to_csv(str(out))
        assert Path(path).exists()
        content = out.read_text()
        assert "id,val" in content
        assert "1,x" in content
        assert "2,y" in content

    def test_to_json(self, tmp_path):
        r = QueryResult(
            columns=["id", "val"],
            rows=[(1, "x"), (2, "y")],
            row_count=2,
            execution_time_ms=1.0,
        )
        out = tmp_path / "test.json"
        path = r.to_json(str(out))
        assert Path(path).exists()
        data = json.loads(out.read_text())
        assert data["row_count"] == 2
        assert len(data["rows"]) == 2
        assert data["rows"][0]["id"] == 1

    def test_empty(self):
        r = QueryResult(columns=[], rows=[], row_count=0, execution_time_ms=0)
        assert r.row_count == 0

    def test_to_dataframe_import_error(self):
        r = QueryResult(columns=[], rows=[], row_count=0, execution_time_ms=0)
        with patch.dict("sys.modules", {"pandas": None}):
            with pytest.raises(ImportError):
                r.to_dataframe()


# ==================== 工厂函数测试 ====================

class TestConnectorFactory:
    """Connector 工厂函数测试"""

    def test_create_mysql(self, mysql_config):
        conn = create_connector("mysql", mysql_config)
        assert conn.connector_name == "mysql"

    def test_create_clickhouse(self, ch_config):
        conn = create_connector("clickhouse", ch_config)
        assert conn.connector_name == "clickhouse"

    def test_create_postgres(self, pg_config):
        conn = create_connector("postgres", pg_config)
        assert conn.connector_name == "postgres"

    def test_create_hive(self, hive_config):
        conn = create_connector("hive", hive_config)
        assert conn.connector_name == "hive"

    def test_create_oracle(self, oracle_config):
        conn = create_connector("oracle", oracle_config)
        assert conn.connector_name == "oracle"

    def test_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown connector type"):
            create_connector("unknown")

    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("MYSQL_HOST", "env-host")
        monkeypatch.setenv("MYSQL_PORT", "3306")
        monkeypatch.setenv("MYSQL_DATABASE", "env-db")
        monkeypatch.setenv("MYSQL_USER", "env-user")
        monkeypatch.setenv("MYSQL_PASSWORD", "env-pass")
        conn = create_connector("mysql", {})
        assert conn.config["host"] == "env-host"
        assert conn.config["database"] == "env-db"


# ==================== SQL 安全测试 ====================

class TestSQLSecurity:
    """SQL 安全 — FORBIDDEN_SQL 拦截"""

    def test_select_allowed(self, mysql_config):
        conn = create_connector("mysql", mysql_config)
        conn.connect = MagicMock()
        conn._do_execute = MagicMock(
            return_value=QueryResult(["c"], [(1,)], 1, 0.1)
        )
        conn._connection = MagicMock()

        result = conn.execute("SELECT 1")
        assert result.row_count == 1

    def test_drop_blocked(self, mysql_config):
        conn = create_connector("mysql", mysql_config)
        conn.connect = MagicMock()
        conn._connection = MagicMock()

        with pytest.raises(RuntimeError, match="Write operation blocked"):
            conn.execute("DROP TABLE users")

    def test_delete_blocked(self, mysql_config):
        conn = create_connector("mysql", mysql_config)
        with pytest.raises(RuntimeError, match="Write operation blocked"):
            conn.execute("DELETE FROM users WHERE id=1")

    def test_insert_blocked(self, mysql_config):
        conn = create_connector("mysql", mysql_config)
        with pytest.raises(RuntimeError, match="Write operation blocked"):
            conn.execute("INSERT INTO users VALUES (1)")

    def test_update_blocked(self, mysql_config):
        conn = create_connector("mysql", mysql_config)
        with pytest.raises(RuntimeError, match="Write operation blocked"):
            conn.execute("UPDATE users SET name='x'")

    def test_truncate_blocked(self, mysql_config):
        conn = create_connector("mysql", mysql_config)
        with pytest.raises(RuntimeError, match="Write operation blocked"):
            conn.execute("TRUNCATE TABLE users")

    def test_alter_blocked(self, mysql_config):
        conn = create_connector("mysql", mysql_config)
        with pytest.raises(RuntimeError, match="Write operation blocked"):
            conn.execute("ALTER TABLE users ADD COLUMN x INT")


# ==================== 配置验证测试 ====================

class TestConfigValidation:
    """配置验证测试"""

    def test_missing_required_raises(self):
        with pytest.raises(ValueError, match="Missing required config"):
            create_connector("mysql", {})


# ==================== MySQL Connector 测试 ====================

class TestMySQLConnector:
    """MySQL 连接器测试 (mock pymysql)"""

    @pytest.fixture(autouse=True)
    def _mock_pymysql(self, mock_cursor):
        mock_module = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_module.connect.return_value = mock_conn
        with patch.dict("sys.modules", {"pymysql": mock_module}):
            yield mock_module

    def test_connect(self, mysql_config):
        conn = create_connector("mysql", mysql_config)
        conn.connect()
        assert conn._connection is not None

    def test_disconnect(self, mysql_config):
        conn = create_connector("mysql", mysql_config)
        conn.connect()
        conn.disconnect()
        assert conn._connection is None

    def test_execute_query(self, mysql_config):
        conn = create_connector("mysql", mysql_config)
        conn.connect()
        result = conn.execute("SELECT * FROM test_orders LIMIT 2")
        assert result.row_count == 2
        assert "name" in result.columns
        assert result.rows[0][0] == 1

    def test_context_manager(self, mysql_config):
        with create_connector("mysql", mysql_config) as conn:
            assert conn._connection is not None
        assert conn._connection is None

    def test_export_csv(self, mysql_config, tmp_path):
        conn = create_connector("mysql", mysql_config)
        conn.connect = MagicMock()
        conn._do_execute = MagicMock(
            return_value=QueryResult(
                ["id"], [(1,), (2,)], 2, 0.5
            )
        )
        conn._connection = MagicMock()

        out = tmp_path / "export.csv"
        path = conn.export("SELECT id FROM t", str(out))
        assert Path(path).exists()

    def test_export_json(self, mysql_config, tmp_path):
        conn = create_connector("mysql", mysql_config)
        conn.connect = MagicMock()
        conn._do_execute = MagicMock(
            return_value=QueryResult(["id"], [(1,)], 1, 0.5)
        )
        conn._connection = MagicMock()

        out = tmp_path / "export.json"
        path = conn.export("SELECT id FROM t", str(out), format="json")
        assert Path(path).exists()


# ==================== ClickHouse Connector 测试 ====================

class TestClickHouseConnector:
    """ClickHouse 连接器测试 (mock clickhouse_driver)"""

    @pytest.fixture(autouse=True)
    def _mock_driver(self, mock_cursor):
        mock_module = MagicMock()
        mock_client = MagicMock()
        mock_client.execute.return_value = (
            [(1, "Alice", 100.0), (2, "Bob", 200.0)],
            [("id", "Int32"), ("name", "String"), ("amount", "Float64")],
        )
        mock_module.Client.return_value = mock_client
        with patch.dict("sys.modules", {"clickhouse_driver": mock_module}):
            yield mock_module

    def test_connect(self, ch_config):
        conn = create_connector("clickhouse", ch_config)
        conn.connect()
        assert conn._connection is not None

    def test_execute_query(self, ch_config):
        conn = create_connector("clickhouse", ch_config)
        conn.connect()
        result = conn.execute("SELECT * FROM test_orders LIMIT 2")
        assert result.row_count == 2
        assert "name" in result.columns

    def test_disconnect(self, ch_config):
        conn = create_connector("clickhouse", ch_config)
        conn.connect()
        conn.disconnect()
        assert conn._connection is None


# ==================== PostgreSQL Connector 测试 ====================

class TestPostgreSQLConnector:
    """PostgreSQL 连接器测试 (mock psycopg2)"""

    @pytest.fixture(autouse=True)
    def _mock_psycopg2(self, mock_cursor):
        mock_module = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_module.connect.return_value = mock_conn
        with patch.dict("sys.modules", {"psycopg2": mock_module}):
            yield mock_module

    def test_connect(self, pg_config):
        conn = create_connector("postgres", pg_config)
        conn.connect()
        assert conn._connection is not None

    def test_execute_query(self, pg_config):
        conn = create_connector("postgres", pg_config)
        conn.connect()
        result = conn.execute("SELECT * FROM test_orders LIMIT 2")
        assert result.row_count == 2
        assert "name" in result.columns

    def test_query_error_rollback(self, pg_config):
        conn = create_connector("postgres", pg_config)
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = RuntimeError("connection failed")
        conn._connection = mock_conn

        with pytest.raises(RuntimeError):
            conn.execute("SELECT 1")


# ==================== Hive Connector 测试 ====================

class TestHiveConnector:
    """Hive 连接器测试 (mock pyhive)"""

    @pytest.fixture(autouse=True)
    def _mock_pyhive(self, mock_cursor):
        mock_hive_module = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_hive_module.connect.return_value = mock_conn
        mock_pyhive = MagicMock()
        mock_pyhive.hive = mock_hive_module
        with patch.dict("sys.modules", {"pyhive": mock_pyhive}):
            yield mock_hive_module

    def test_connect(self, hive_config):
        conn = create_connector("hive", hive_config)
        conn.connect()
        assert conn._connection is not None

    def test_execute_query(self, hive_config):
        conn = create_connector("hive", hive_config)
        conn.connect()
        result = conn.execute("SELECT * FROM test_orders LIMIT 2")
        assert result.row_count == 2

    def test_query_error_rollback(self, hive_config):
        conn = create_connector("hive", hive_config)
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = RuntimeError("hive error")
        conn._connection = mock_conn

        with pytest.raises(RuntimeError):
            conn.execute("SELECT 1")


# ==================== Oracle Connector 测试 ====================

class TestOracleConnector:
    """Oracle 连接器测试 (mock oracledb)"""

    @pytest.fixture(autouse=True)
    def _mock_oracledb(self, mock_cursor):
        mock_module = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_module.connect.return_value = mock_conn
        mock_module.makedsn.return_value = "mock_dsn"
        mock_module.AUTH_MODE_SYSDBA = 2
        mock_module.DEFAULT_AUTH = 0
        with patch.dict("sys.modules", {"oracledb": mock_module}):
            yield mock_module

    def test_connect(self, oracle_config):
        conn = create_connector("oracle", oracle_config)
        conn.connect()
        assert conn._connection is not None

    def test_execute_query(self, oracle_config):
        conn = create_connector("oracle", oracle_config)
        conn.connect()
        result = conn.execute("SELECT * FROM test_orders")
        assert result.row_count == 2

    def test_rownum_limit_param(self, oracle_config):
        conn = create_connector("oracle", oracle_config)
        conn.connect()
        result = conn.execute(
            "SELECT * FROM test_orders WHERE ROWNUM <= :rownum_limit",
            {"rownum_limit": 10},
        )
        assert result.row_count == 2


# ==================== 通用错误处理测试 ====================

class TestConnectorErrorHandling:
    """通用连接器错误处理测试"""

    def test_connection_failure_logs_error(self, mysql_config):
        mock_module = MagicMock()
        mock_module.connect.side_effect = RuntimeError("Connection refused")
        with patch.dict("sys.modules", {"pymysql": mock_module}):
            conn = create_connector("mysql", mysql_config)
            with pytest.raises(RuntimeError):
                conn.connect()

    def test_import_error_improperly_installed(self, mysql_config):
        """模拟 pymysql 未安装"""
        conn = create_connector("mysql", mysql_config)
        conn.config = mysql_config
        with patch.dict("sys.modules", {"pymysql": None}):
            conn._connection = None
            with pytest.raises(ImportError, match="pymysql is required"):
                conn.connect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
