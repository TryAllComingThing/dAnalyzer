"""
Base Connector - 所有数据源连接器的基类
"""

import os
import re
import csv
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """查询结果数据结构"""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time_ms: float
    format: str = "csv"

    def to_csv(self, output_path: str) -> str:
        """导出为CSV格式"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(self.columns)
            writer.writerows(self.rows)
        return output_path

    def to_json(self, output_path: str) -> str:
        """导出为JSON格式"""
        data = {
            "columns": self.columns,
            "rows": [dict(zip(self.columns, row)) for row in self.rows],
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path

    def to_dataframe(self):
        """转换为pandas DataFrame"""
        try:
            import pandas as pd
            return pd.DataFrame(self.rows, columns=self.columns)
        except ImportError:
            raise ImportError("pandas is required for to_dataframe()")


class BaseConnector(ABC):
    """数据源连接器基类"""

    # 子类必须覆盖
    connector_name: str = ""
    default_timeout: int = 120000  # 毫秒
    default_max_rows: int = 10000

    def __init__(self, config: Optional[Dict[str, str]] = None):
        """
        初始化连接器

        Args:
            config: 连接配置，支持从环境变量读取
        """
        self.config = config or {}
        self._connection = None
        self._validate_config()

    def _validate_config(self):
        """验证必要配置"""
        required = self.get_required_config()
        for key in required:
            if key not in self.config or not self.config[key]:
                # 尝试从环境变量读取
                env_key = f"{self.connector_name.upper()}_{key.upper()}"
                value = os.environ.get(env_key)
                if value:
                    self.config[key] = value
                else:
                    raise ValueError(f"Missing required config: {key}")

    @abstractmethod
    def get_required_config(self) -> List[str]:
        """返回必需的配置项"""
        pass

    @abstractmethod
    def _do_connect(self):
        """建立连接 - 子类实现"""
        pass

    @abstractmethod
    def _do_disconnect(self):
        """关闭连接 - 子类实现"""
        pass

    @abstractmethod
    def _do_execute(self, sql: str, params: Optional[Dict] = None) -> QueryResult:
        """执行查询 - 子类实现"""
        pass

    def connect(self):
        """建立连接"""
        if self._connection is None:
            logger.info(f"[{self.connector_name}] Connecting...")
            self._connection = self._do_connect()
            logger.info(f"[{self.connector_name}] Connected successfully")
        return self

    def disconnect(self):
        """关闭连接"""
        if self._connection is not None:
            logger.info(f"[{self.connector_name}] Disconnecting...")
            self._do_disconnect()
            self._connection = None
            logger.info(f"[{self.connector_name}] Disconnected")

    FORBIDDEN_SQL = re.compile(
        r'\b(DROP|DELETE|TRUNCATE|ALTER|CREATE|INSERT|UPDATE|GRANT|REVOKE)\b',
        re.IGNORECASE
    )

    def execute(self, sql: str, params: Optional[Dict] = None) -> QueryResult:
        """
        执行SQL查询（只读）

        Args:
            sql: SELECT 查询语句
            params: 查询参数

        Returns:
            QueryResult: 查询结果
        """
        if self.FORBIDDEN_SQL.search(sql):
            raise RuntimeError(
                f"Write operation blocked by connector-level security. "
                f"Only SELECT queries are permitted."
            )
        if self._connection is None:
            self.connect()

        logger.info(f"[{self.connector_name}] Executing: {sql[:100]}...")
        result = self._do_execute(sql, params)
        logger.info(f"[{self.connector_name}] Returned {result.row_count} rows")
        return result

    def export(self, sql: str, output_path: str, format: str = "csv") -> str:
        """
        执行查询并导出结果

        Args:
            sql: SQL语句
            output_path: 输出文件路径
            format: 输出格式 (csv/json)

        Returns:
            输出文件路径
        """
        result = self.execute(sql)
        result.format = format

        if format == "csv":
            return result.to_csv(output_path)
        elif format == "json":
            return result.to_json(output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.disconnect()


def create_connector(connector_type: str, config: Dict[str, str] = None):
    """
    工厂函数：创建连接器实例

    Args:
        connector_type: 连接器类型 (mysql, clickhouse, hive, postgres, oracle)
        config: 连接配置

    Returns:
        BaseConnector: 连接器实例
    """
    connector_map = {
        'mysql': 'MySQLConnector',
        'clickhouse': 'ClickHouseConnector',
        'hive': 'HiveConnector',
        'postgres': 'PostgreSQLConnector',
        'oracle': 'OracleConnector',
    }

    if connector_type not in connector_map:
        raise ValueError(f"Unknown connector type: {connector_type}")

    module = __import__(
        f'connectors.datawarehouse.{connector_type}',
        fromlist=[connector_map[connector_type]]
    )
    connector_class = getattr(module, connector_map[connector_type])
    return connector_class(config)
