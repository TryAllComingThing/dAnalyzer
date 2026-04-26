# -*- coding: utf-8 -*-
"""
MySQL Connector 单元测试
测试用例: TC-MYSQL-001 ~ TC-MYSQL-033
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from connectors.datawarehouse.base import QueryResult


class TestMySQLConnectorConnection:
    """连接管理测试"""

    def test_connect_success(self, mysql_config):
        """TC-MYSQL-001: 正常连接测试"""
        from connectors import create_connector

        # 跳过实际连接测试，只验证创建
        conn = create_connector("mysql", mysql_config)
        assert conn is not None
        assert conn.connector_name == "mysql"

    def test_connect_missing_config(self):
        """TC-MYSQL-002: 缺失配置测试"""
        from connectors import create_connector

        with pytest.raises(ValueError, match="Missing required config"):
            create_connector("mysql", {})

    def test_missing_host(self):
        """TC-MYSQL-002b: 缺失 host 测试"""
        from connectors import create_connector

        config = {"port": 3306, "database": "test", "user": "root", "password": "root"}
        with pytest.raises(ValueError, match="Missing required config"):
            create_connector("mysql", config)

    def test_environment_variable_fallback(self):
        """TC-MYSQL-003: 环境变量回退测试"""
        from connectors import create_connector

        # 设置环境变量
        os.environ["MYSQL_HOST"] = "test-host"
        os.environ["MYSQL_PORT"] = "3307"
        os.environ["MYSQL_DATABASE"] = "testdb"
        os.environ["MYSQL_USER"] = "testuser"
        os.environ["MYSQL_PASSWORD"] = "testpass"

        try:
            conn = create_connector("mysql", {})
            # 验证环境变量被读取
            assert conn.config.get("host") == "test-host"
            assert conn.config.get("port") == "3307"
        finally:
            # 清理环境变量
            for key in ["MYSQL_HOST", "MYSQL_PORT", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD"]:
                os.environ.pop(key, None)

    def test_context_manager(self, mysql_config):
        """TC-MYSQL-006: 上下文管理器测试"""
        from connectors import create_connector

        # 使用 mock 避免实际连接
        with patch("connectors.datawarehouse.mysql.pymysql") as mock_pymysql:
            mock_conn = MagicMock()
            mock_pymysql.connect.return_value = mock_conn

            with create_connector("mysql", mysql_config) as conn:
                assert conn._connection is not None

            # 验证 disconnect 被调用
            mock_conn.close.assert_called_once()


class TestMySQLConnectorQuery:
    """查询执行测试"""

    @pytest.fixture
    def mock_connector(self, mysql_config):
        """创建带 mock 连接的 connector"""
        from connectors import create_connector

        with patch("connectors.datawarehouse.mysql.pymysql") as mock_pymysql:
            mock_connection = MagicMock()
            mock_cursor = MagicMock()

            # 设置 cursor description 模拟查询结果
            mock_cursor.description = [
                ("order_id",),
                ("user_id",),
                ("amount",),
            ]
            mock_cursor.fetchmany.return_value = [
                ("O001", "U001", 100.0),
                ("O002", "U002", 200.0),
            ]

            mock_connection.cursor.return_value = mock_cursor
            mock_connection.commit = MagicMock()
            mock_pymysql.connect.return_value = mock_connection

            conn = create_connector("mysql", mysql_config)
            conn.connect()
            yield conn, mock_cursor

    def test_simple_query(self, mock_connector):
        """TC-MYSQL-010: 简单查询测试"""
        conn, mock_cursor = mock_connector

        result = conn.execute("SELECT order_id, user_id, amount FROM test_orders LIMIT 10")

        assert result.row_count == 2
        assert result.columns == ["order_id", "user_id", "amount"]
        assert len(result.rows) == 2

    def test_aggregation_query(self, mock_connector):
        """TC-MYSQL-011: 聚合查询测试"""
        conn, mock_cursor = mock_connector

        # 修改 mock 返回聚合结果
        mock_cursor.description = [("cnt",), ("total",)]
        mock_cursor.fetchmany.return_value = [(100, 50000.0)]

        result = conn.execute("SELECT COUNT(*) as cnt, SUM(amount) as total FROM test_orders")

        assert result.row_count == 1
        assert result.rows[0][0] == 100
        assert result.rows[0][1] == 50000.0

    def test_empty_result_set(self, mock_connector):
        """TC-MYSQL-017: 空结果集测试"""
        conn, mock_cursor = mock_connector

        # 模拟空结果
        mock_cursor.fetchmany.return_value = []

        result = conn.execute("SELECT * FROM test_orders WHERE 1=0")

        assert result.row_count == 0
        assert result.rows == []

    def test_parameterized_query(self, mock_connector):
        """TC-MYSQL-016: 参数化查询测试"""
        conn, mock_cursor = mock_connector

        result = conn.execute(
            "SELECT * FROM test_orders WHERE user_id = %(user_id)s",
            {"user_id": "U100001"}
        )

        # 验证参数被正确传递
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "%(user_id)s" in call_args[0][0]
        assert call_args[0][1] == {"user_id": "U100001"}


class TestMySQLConnectorExport:
    """结果导出测试"""

    @pytest.fixture
    def sample_result(self):
        """创建示例 QueryResult"""
        return QueryResult(
            columns=["order_id", "user_id", "amount"],
            rows=[
                ["O001", "U001", 100.0],
                ["O002", "U002", 200.0],
            ],
            row_count=2,
            execution_time_ms=100.0,
        )

    def test_to_csv(self, sample_result, tmp_path):
        """TC-MYSQL-020: CSV 导出测试"""
        output_path = tmp_path / "test.csv"

        result = sample_result.to_csv(str(output_path))

        assert output_path.exists()
        content = output_path.read_text()
        assert "order_id,user_id,amount" in content
        assert "O001,U001,100.0" in content

    def test_to_json(self, sample_result, tmp_path):
        """TC-MYSQL-021: JSON 导出测试"""
        output_path = tmp_path / "test.json"

        result = sample_result.to_json(str(output_path))

        assert output_path.exists()
        import json
        data = json.loads(output_path.read_text())
        assert "columns" in data
        assert "rows" in data
        assert data["row_count"] == 2

    def test_to_dataframe(self, sample_result):
        """TC-MYSQL-022: DataFrame 转换测试"""
        df = sample_result.to_dataframe()

        assert len(df) == 2
        assert list(df.columns) == ["order_id", "user_id", "amount"]


class TestMySQLConnectorError:
    """错误处理测试"""

    def test_sql_syntax_error(self, mysql_config):
        """TC-MYSQL-030: SQL 语法错误测试"""
        from connectors import create_connector

        with patch("connectors.datawarehouse.mysql.pymysql") as mock_pymysql:
            mock_connection = MagicMock()
            mock_cursor = MagicMock()

            # 模拟 SQL 语法错误
            mock_cursor.execute.side_effect = Exception("You have an error in your SQL syntax")
            mock_connection.cursor.return_value = mock_cursor
            mock_pymysql.connect.return_value = mock_connection

            conn = create_connector("mysql", mysql_config)
            conn.connect()

            with pytest.raises(RuntimeError, match="MySQL query failed"):
                conn.execute("SELECT XXX FROM YYY")

    def test_table_not_exists(self, mysql_config):
        """TC-MYSQL-031: 表不存在测试"""
        from connectors import create_connector

        with patch("connectors.datawarehouse.mysql.pymysql") as mock_pymysql:
            mock_connection = MagicMock()
            mock_cursor = MagicMock()

            # 模拟表不存在错误
            mock_cursor.execute.side_effect = Exception("Table 'danalyzer_test.non_existent' doesn't exist")
            mock_connection.cursor.return_value = mock_cursor
            mock_pymysql.connect.return_value = mock_connection

            conn = create_connector("mysql", mysql_config)
            conn.connect()

            with pytest.raises(RuntimeError):
                conn.execute("SELECT * FROM non_existent_table")


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
