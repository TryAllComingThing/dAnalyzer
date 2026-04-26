"""
dAnalyzer Connectors - Datawarehouse Module

支持多种数据仓库的连接和查询
"""

from .base import BaseConnector, QueryResult

__all__ = ['BaseConnector', 'QueryResult']

# 便捷导入
from .mysql import MySQLConnector
from .clickhouse import ClickHouseConnector
from .hive import HiveConnector
from .postgres import PostgreSQLConnector
from .oracle import OracleConnector

__all__.extend([
    'MySQLConnector',
    'ClickHouseConnector',
    'HiveConnector',
    'PostgreSQLConnector',
    'OracleConnector',
])
