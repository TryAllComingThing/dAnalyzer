"""
ClickHouse Connector

参考: connectors/datawarehouse/clickhouse-connector.md
"""

import time
from typing import Optional, Dict, List
from .base import BaseConnector, QueryResult


class ClickHouseConnector(BaseConnector):
    """ClickHouse OLAP数据库连接器"""

    connector_name = "clickhouse"
    default_timeout = 300000  # 5分钟

    def get_required_config(self) -> List[str]:
        return ["host", "port", "database", "user", "password"]

    def _do_connect(self):
        """建立ClickHouse连接"""
        try:
            from clickhouse_driver import Client
            return Client(
                host=self.config.get("host", "localhost"),
                port=int(self.config.get("port", 9000)),
                database=self.config.get("database", "default"),
                user=self.config.get("user", "default"),
                password=self.config.get("password", ""),
                connect_timeout=self.default_timeout / 1000,
                send_receive_timeout=self.default_timeout / 1000,
            )
        except ImportError:
            raise ImportError("clickhouse-driver is required. Install: pip install clickhouse-driver")

    def _do_disconnect(self):
        """关闭ClickHouse连接"""
        if self._connection:
            self._connection.disconnect()

    def _do_execute(self, sql: str, params: Optional[Dict] = None) -> QueryResult:
        """执行ClickHouse查询"""
        start_time = time.time()

        try:
            # ClickHouse使用 settings 传递参数
            settings = {}
            if params:
                settings['parameters'] = params

            result = self._connection.execute(sql, with_column_types=True, settings=settings)

            # 解析结果
            if result and len(result) == 2:
                rows = result[0]
                column_types = result[1]
                columns = [col[0] for col in column_types]
            else:
                rows = result or []
                columns = []

            row_count = len(rows)
            # 限制返回行数
            if row_count > self.default_max_rows:
                rows = rows[:self.default_max_rows]
                row_count = self.default_max_rows

        except Exception as e:
            raise RuntimeError(f"ClickHouse query failed: {e}")

        execution_time_ms = (time.time() - start_time) * 1000
        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
        )
