"""
Hive Connector

Uses pyhive or impyla to connect to HiveServer2.
"""

import time
from typing import Optional, Dict, List
from .base import BaseConnector, QueryResult


class HiveConnector(BaseConnector):
    """Hive 数据库连接器"""

    connector_name = "hive"

    def get_required_config(self) -> List[str]:
        return ["host", "port", "database"]

    def _do_connect(self):
        try:
            from pyhive import hive
            return hive.connect(
                host=self.config.get("host", "localhost"),
                port=int(self.config.get("port", 10000)),
                database=self.config.get("database", "default"),
                username=self.config.get("user"),
                password=self.config.get("password"),
                auth=self.config.get("auth", "NONE"),
                configuration=self.config.get("configuration", {}),
            )
        except ImportError:
            try:
                from impala.dbapi import connect as impala_connect
                return impala_connect(
                    host=self.config.get("host", "localhost"),
                    port=int(self.config.get("port", 10000)),
                    database=self.config.get("database", "default"),
                    user=self.config.get("user"),
                    password=self.config.get("password"),
                    auth_mechanism=self.config.get("auth", "NOSASL"),
                )
            except ImportError:
                raise ImportError(
                    "Hive driver required. Install: pip install pyhive or pip install impyla"
                )

    def _do_disconnect(self):
        if self._connection:
            self._connection.close()

    def _do_execute(self, sql: str, params: Optional[Dict] = None) -> QueryResult:
        start_time = time.time()

        cursor = self._connection.cursor()
        try:
            timeout_sec = max(1, self.default_timeout // 1000)
            cursor.execute(f"SET hive.server2.idle.operation.timeout = {timeout_sec * 1000}")
            cursor.execute(sql, params or {})
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchmany(self.default_max_rows)
            row_count = len(rows)
        except Exception as e:
            try:
                self._connection.rollback()
            except Exception:
                pass
            raise RuntimeError(f"Hive query failed: {e}")
        finally:
            cursor.close()

        execution_time_ms = (time.time() - start_time) * 1000
        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
        )
