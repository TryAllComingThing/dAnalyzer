"""
dAnalyzer Connectors - Tool Module

支持文件格式转换和数据处理工具
"""

from .base import BaseFileConnector, FileResult

__all__ = ['BaseFileConnector', 'FileResult']

# 便捷导入
from .csv_connector import CSVConnector
from .json_connector import JSONConnector
from .excel_connector import ExcelConnector
from .python_connector import PythonConnector

__all__.extend([
    'CSVConnector',
    'JSONConnector',
    'ExcelConnector',
    'PythonConnector',
])
