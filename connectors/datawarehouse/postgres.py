"""
PostgreSQL Connector

参考: connectors/datawarehouse/postgres-connector.md
"""

import time
from typing import Optional, Dict, List
from .base import BaseConnector, QueryResult


class PostgreSQLConnector(BaseConnector):
    """PostgreSQL数据库连接器"""

    connector_name = "postgres"

    def get_required_config(self) -> List[str]:
        return ["host", "port", "database", "user", "password"]

    def _do_connect(self):
        """建立PostgreSQL连接"""
        try:
            import psycopg2
            return psycopg2.connect(
                host=self.config.get("host", "localhost"),
                port=int(self.config.get("port", 5432)),
                database=self.config.get("database", ""),
                user=self.config.get("user", ""),
                password=self.config.get("password", ""),
                connect_timeout=self.default_timeout / 1000,
            )
        except ImportError:
            raise ImportError("psycopg2 is required. Install: pip install psycopg2-binary")

    def _do_disconnect(self):
        """关闭PostgreSQL连接"""
        if self._connection:
            self._connection.close()

    def _do_execute(self, sql: str, params: Optional[Dict] = None) -> QueryResult:
        """执行PostgreSQL查询"""
        start_time = time.time()

        cursor = self._connection.cursor()
        try:
            cursor.execute(sql, params or {})

            # 获取列名
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # 获取数据
            rows = cursor.fetchmany(self.default_max_rows)
            row_count = len(rows)

            # 提交事务
            self._connection.commit()

        except Exception as e:
            self._connection.rollback()
            raise RuntimeError(f"PostgreSQL query failed: {e}")
        finally:
            cursor.close()

        execution_time_ms = (time.time() - start_time) * 1000
        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
        )
