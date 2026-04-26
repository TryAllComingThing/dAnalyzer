# -*- coding: utf-8 -*-
"""
data-query 技能集成测试
测试用例: TC-QUERY-001 ~ TC-QUERY-005
"""

import pytest
import csv
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestDataQuerySkill:
    """data-query 技能测试"""

    def test_query_orders_by_date_range(self, orders_csv_data):
        """TC-QUERY-001: 按时间范围查询订单"""
        # 验证数据加载
        assert len(orders_csv_data) > 0

        # 筛选时间范围
        start_date = "2024-01-01"
        end_date = "2024-12-31"

        filtered = [
            row for row in orders_csv_data
            if start_date <= row.get("order_date", "") <= end_date
        ]

        assert len(filtered) > 0

    def test_query_by_multiple_conditions(self, orders_csv_data):
        """TC-QUERY-003: 多条件组合查询"""
        # 按城市 + 金额 + 状态组合查询
        city = "上海"
        min_amount = 1000
        status = "已完成"

        filtered = [
            row for row in orders_csv_data
            if row.get("city") == city
            and float(row.get("actual_amount", 0)) > min_amount
            and row.get("order_status") == status
        ]

        # 验证结果
        for row in filtered:
            assert row["city"] == city
            assert float(row["actual_amount"]) > min_amount
            assert row["order_status"] == status

    def test_export_to_csv(self, orders_csv_data, tmp_path):
        """TC-QUERY-004: 导出为 CSV 格式"""
        # 取前 10 条
        sample_data = orders_csv_data[:10]

        # 导出
        output_path = tmp_path / "query_result.csv"
        columns = list(sample_data[0].keys()) if sample_data else []

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(sample_data)

        # 验证
        assert output_path.exists()
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 10

    def test_sql_injection_blocked(self):
        """TC-QUERY-005: 危险 SQL 拦截"""
        dangerous_sqls = [
            "DROP TABLE test_orders",
            "DELETE FROM test_orders",
            "TRUNCATE TABLE test_orders",
            "INSERT INTO test_orders VALUES (1, 'hack')",
            "UPDATE test_orders SET amount=0",
            "-- comment OR 1=1",
        ]

        def is_safe_sql(sql: str) -> bool:
            """SQL 安全检查"""
            sql_upper = sql.upper().strip()
            dangerous_patterns = [
                "DROP ", "DELETE ", "TRUNCATE ", "INSERT ", "UPDATE ",
                ";--", "OR 1=1", "UNION ALL SELECT"
            ]
            for pattern in dangerous_patterns:
                if pattern in sql_upper:
                    return False
            return True

        for sql in dangerous_sqls:
            assert not is_safe_sql(sql), f"危险 SQL 未被拦截: {sql}"


class TestDataQueryWithConnector:
    """使用 Connector 进行数据查询测试"""

    def test_query_via_connector(self, mysql_config):
        """使用 MySQL Connector 进行查询"""
        from connectors import create_connector

        # Mock 连接
        with patch("connectors.datawarehouse.mysql.pymysql") as mock_pymysql:
            mock_connection = MagicMock()
            mock_cursor = MagicMock()

            # 模拟查询结果
            mock_cursor.description = [
                ("order_id",), ("user_id",), ("actual_amount",), ("order_date",)
            ]
            mock_cursor.fetchmany.return_value = [
                ("O2024000001", "U100001", 100.0, "2024-01-01"),
                ("O2024000002", "U100002", 200.0, "2024-01-02"),
            ]

            mock_connection.cursor.return_value = mock_cursor
            mock_connection.commit = MagicMock()
            mock_pymysql.connect.return_value = mock_connection

            # 执行查询
            conn = create_connector("mysql", mysql_config)
            result = conn.execute("""
                SELECT order_id, user_id, actual_amount, order_date
                FROM test_orders
                WHERE order_date >= '2024-01-01'
                LIMIT 100
            """)

            assert result.row_count == 2
            assert "order_id" in result.columns
            assert "actual_amount" in result.columns


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
