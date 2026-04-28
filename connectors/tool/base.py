"""
Base File Connector - 文件类连接器基类
"""

import os
import csv
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FileResult:
    """文件操作结果"""
    success: bool
    output_path: Optional[str] = None
    row_count: int = 0
    columns: List[str] = None
    raw_data: Any = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.columns is None:
            self.columns = []


class BaseFileConnector(ABC):
    """文件类连接器基类"""

    connector_name = ""
    supported_formats = []

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    def read(self, file_path: str, **kwargs) -> FileResult:
        """读取文件"""
        pass

    @abstractmethod
    def write(self, data: List[Dict], file_path: str, **kwargs) -> FileResult:
        """写入文件"""
        pass

    def _ensure_dir(self, file_path: str):
        """确保目录存在"""
        dir_path = os.path.dirname(file_path)
        if dir_path:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    def _parse_kwargs(self, kwargs: Dict, defaults: Dict) -> Dict:
        """合并默认配置"""
        result = defaults.copy()
        result.update(kwargs)
        return result


def create_tool_connector(connector_type: str, config: Dict[str, Any] = None):
    """
    工厂函数：创建工具连接器实例

    Args:
        connector_type: 连接器类型 (csv, json, excel, python)
        config: 配置

    Returns:
        BaseFileConnector: 连接器实例
    """
    connector_map = {
        'csv': 'CSVConnector',
        'json': 'JSONConnector',
        'excel': 'ExcelConnector',
        'python': 'PythonConnector',
    }

    if connector_type not in connector_map:
        raise ValueError(f"Unknown connector type: {connector_type}")

    module = __import__(
        f'connectors.tool.{connector_type}_connector',
        fromlist=[connector_map[connector_type]]
    )
    connector_class = getattr(module, connector_map[connector_type])
    return connector_class(config)
