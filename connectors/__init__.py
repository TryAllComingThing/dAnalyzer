"""
dAnalyzer Connectors — 统一数据源连接器

Usage:
    from connectors import create_connector, create_tool_connector

    db = create_connector("mysql", {"host": "...", "database": "...", "user": "...", "password": "..."})
    result = db.execute("SELECT 1")

    csv = create_tool_connector("csv")
    result = csv.read("knowledge/file.csv")
"""

from connectors.datawarehouse.base import create_connector
from connectors.tool.base import create_tool_connector

__all__ = ["create_connector", "create_tool_connector"]
