"""
Oracle Connector

参考: connectors/datawarehouse/oracle-connector.md
"""

import time
from typing import Optional, Dict, List
from .base import BaseConnector, QueryResult


class OracleConnector(BaseConnector):
    """Oracle Database连接器"""

    connector_name = "oracle"
    default_timeout = 300000  # 5分钟

    def get_required_config(self) -> List[str]:
        return ["host", "port", "service", "user", "password"]

    def _do_connect(self):
        """建立Oracle连接"""
        try:
            # 优先使用新版 oracledb (-thin模式无需Oracle客户端)
            import oracledb
            dsn = oracledb.makedsn(
                self.config.get("host", "localhost"),
                int(self.config.get("port", 1521)),
                service_name=self.config.get("service", "ORCL")
            )
            return oracledb.connect(
                user=self.config.get("user", ""),
                password=self.config.get("password", ""),
                dsn=dsn,
                mode=oracledb.AUTH_MODE_SYSDBA if self.config.get("sysdba", False) else oracledb.DEFAULT_AUTH,
            )
        except ImportError:
            try:
                # 回退到旧版 cx_Oracle
                import cx_Oracle
                dsn = cx_Oracle.makedsn(
                    self.config.get("host", "localhost"),
                    int(self.config.get("port", 1521)),
                    service_name=self.config.get("service", "ORCL")
                )
                return cx_Oracle.connect(
                    self.config.get("user", ""),
                    self.config.get("password", ""),
                    dsn=dsn,
                )
            except ImportError:
                raise ImportError("oracledb or cx_Oracle is required. Install: pip install oracledb")

    def _do_disconnect(self):
        """关闭Oracle连接"""
        if self._connection:
            self._connection.close()

    def _do_execute(self, sql: str, params: Optional[Dict] = None) -> QueryResult:
        """执行Oracle查询"""
        start_time = time.time()

        cursor = self._connection.cursor()
        try:
            # 处理ROWNUM_LIMIT语法
            if params and 'rownum_limit' in params:
                sql = sql.replace(':rownum_limit', str(params['rownum_limit']))

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
            raise RuntimeError(f"Oracle query failed: {e}")
        finally:
            cursor.close()

        execution_time_ms = (time.time() - start_time) * 1000
        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
        )
