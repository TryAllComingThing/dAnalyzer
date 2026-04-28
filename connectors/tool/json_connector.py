"""
JSON Connector

参考: connectors/tool/json-connector.md
"""

import json
import gzip
import logging
from typing import List, Dict, Any, Optional
from .base import BaseFileConnector, FileResult


logger = logging.getLogger(__name__)


class JSONConnector(BaseFileConnector):
    """JSON文件连接器"""

    connector_name = "json"
    supported_formats = ["json", "jsonl"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.encoding = self.config.get("encoding", "utf-8")

    def read(self, file_path: str, **kwargs) -> FileResult:
        """
        读取JSON文件

        Args:
            file_path: 文件路径
            encoding: 编码
            format: 格式 (array=数组格式, object=对象格式)
            compression: 压缩格式 (None, gzip)
        """
        opts = self._parse_kwargs(kwargs, {
            "encoding": self.encoding,
            "format": "array",
            "compression": None,
        })

        try:
            # 处理压缩文件
            open_func = open
            if opts.get("compression") == "gzip" or file_path.endswith(".gz"):
                import gzip
                open_func = lambda p, m: gzip.open(p, m, encoding=opts["encoding"])

            with open_func(file_path, 'r') as f:
                data = json.load(f)

            # 统一转换为数组格式
            if opts["format"] == "object":
                # {"data": [...], "total": N} -> [...]
                if isinstance(data, dict):
                    if "data" in data:
                        data = data["data"]
                    elif "rows" in data:
                        data = data["rows"]
                    elif "items" in data:
                        data = data["items"]

            if not isinstance(data, list):
                data = [data]

            # 提取列名
            columns = []
            if data:
                columns = list(data[0].keys())

            row_count = len(data)
            logger.info(f"[JSON] Read {row_count} rows from {file_path}")

            return FileResult(
                success=True,
                output_path=file_path,
                row_count=row_count,
                columns=columns,
                raw_data=data,
            )

        except Exception as e:
            logger.error(f"[JSON] Read failed: {e}")
            return FileResult(success=False, error=str(e))

    def write(self, data: List[Dict], file_path: str, **kwargs) -> FileResult:
        """
        写入JSON文件

        Args:
            data: 数据列表
            file_path: 输出路径
            encoding: 编码
            format: 格式 (array=数组, object=包装对象)
            indent: 缩进空格数 (None=紧凑格式)
            compression: 压缩格式
        """
        opts = self._parse_kwargs(kwargs, {
            "encoding": self.encoding,
            "format": "array",
            "indent": 2,
            "compression": None,
        })

        if not data:
            return FileResult(success=False, error="No data to write")

        try:
            self._ensure_dir(file_path)

            # 构建输出数据
            if opts["format"] == "object":
                output_data = {
                    "data": data,
                    "total": len(data)
                }
            else:
                output_data = data

            # 处理压缩
            if opts.get("compression") == "gzip" or file_path.endswith(".gz"):
                import gzip
                with gzip.open(file_path, 'wt', encoding=opts["encoding"]) as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=opts["indent"])
            else:
                with open(file_path, 'w', encoding=opts["encoding"]) as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=opts["indent"])

            row_count = len(data)
            columns = list(data[0].keys()) if data else []

            logger.info(f"[JSON] Wrote {row_count} rows to {file_path}")

            return FileResult(
                success=True,
                output_path=file_path,
                row_count=row_count,
                columns=columns,
            )

        except Exception as e:
            logger.error(f"[JSON] Write failed: {e}")
            return FileResult(success=False, error=str(e))

    def flatten(self, data: Dict) -> Dict:
        """
        扁平化嵌套JSON

        {"user": {"name": "Tom", "age": 30}}
        ->
        {"user_name": "Tom", "user_age": 30}
        """
        result = {}

        def _flatten(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}_{key}" if prefix else key
                    _flatten(value, new_key)
            elif isinstance(obj, list):
                # 列表转为JSON字符串
                result[prefix] = json.dumps(obj, ensure_ascii=False)
            else:
                result[prefix] = obj

        _flatten(data)
        return result
