"""
MySQL Connector

参考: connectors/datawarehouse/mysql-connector.md
"""

import time
from typing import Optional, Dict, List
from .base import BaseConnector, QueryResult


class MySQLConnector(BaseConnector):
    """MySQL数据库连接器"""

    connector_name = "mysql"

    def get_required_config(self) -> List[str]:
        return ["host", "port", "database", "user", "password"]

    def _do_connect(self):
        """建立MySQL连接"""
        try:
            import pymysql
            return pymysql.connect(
                host=self.config.get("host", "localhost"),
                port=int(self.config.get("port", 3306)),
                database=self.config.get("database", "test"),
                user=self.config.get("user", "root"),
                password=self.config["password"],
                charset=self.config.get("charset", "utf8mb4"),
                connect_timeout=self.default_timeout / 1000,
            )
        except ImportError:
            raise ImportError("pymysql is required. Install: pip install pymysql")

    def _do_disconnect(self):
        """关闭MySQL连接"""
        if self._connection:
            self._connection.close()

    def _do_execute(self, sql: str, params: Optional[Dict] = None) -> QueryResult:
        """执行MySQL查询"""
        start_time = time.time()

        cursor = self._connection.cursor()
        try:
            timeout_ms = int(self.default_timeout)
            cursor.execute(f"SET SESSION max_execution_time = {timeout_ms}")
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
            raise RuntimeError(f"MySQL query failed: {e}")
        finally:
            cursor.close()

        execution_time_ms = (time.time() - start_time) * 1000
        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
        )
