"""
CSV Connector

参考: connectors/tool/csv-connector.md
"""

import csv
import gzip
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from .base import BaseFileConnector, FileResult


logger = logging.getLogger(__name__)


class CSVConnector(BaseFileConnector):
    """CSV文件连接器"""

    connector_name = "csv"
    supported_formats = ["csv", "tsv", "txt"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.delimiter = self.config.get("delimiter", ",")
        self.encoding = self.config.get("encoding", "utf-8")
        self.has_header = self.config.get("has_header", True)

    def read(self, file_path: str, **kwargs) -> FileResult:
        """
        读取CSV文件

        Args:
            file_path: 文件路径
            delimiter: 分隔符 (默认逗号)
            encoding: 编码 (默认utf-8)
            has_header: 是否有表头 (默认True)
            max_rows: 最大读取行数
            compression: 压缩格式 (None, gzip)
        """
        opts = self._parse_kwargs(kwargs, {
            "delimiter": self.delimiter,
            "encoding": self.encoding,
            "has_header": self.has_header,
            "max_rows": None,
            "compression": None,
        })

        try:
            # 处理压缩文件
            open_func = open
            if opts.get("compression") == "gzip" or file_path.endswith(".gz"):
                import gzip
                open_func = gzip.open

            with open_func(file_path, 'r', encoding=opts["encoding"]) as f:
                reader = csv.reader(f, delimiter=opts["delimiter"])

                columns = []
                rows = []

                if opts["has_header"]:
                    try:
                        columns = next(reader)
                    except StopIteration:
                        columns = []
                else:
                    try:
                        first_row = next(reader)
                    except StopIteration:
                        first_row = None
                    if first_row:
                        columns = [f"col_{i}" for i in range(len(first_row))]
                        rows.append(first_row)

                # 读取数据
                for i, row in enumerate(reader):
                    if opts["max_rows"] and i >= opts["max_rows"]:
                        break
                    rows.append(row)

                row_count = len(rows)
                logger.info(f"[CSV] Read {row_count} rows from {file_path}")

                return FileResult(
                    success=True,
                    output_path=file_path,
                    row_count=row_count,
                    columns=columns,
                )

        except Exception as e:
            logger.error(f"[CSV] Read failed: {e}")
            return FileResult(success=False, error=str(e))

    def write(self, data: List[Dict], file_path: str, **kwargs) -> FileResult:
        """
        写入CSV文件

        Args:
            data: 数据列表
            file_path: 输出路径
            delimiter: 分隔符 (默认逗号)
            encoding: 编码 (默认utf-8)
            write_header: 是否写入表头 (默认True)
            mode: 写入模式 (w=覆盖, a=追加)
        """
        opts = self._parse_kwargs(kwargs, {
            "delimiter": self.delimiter,
            "encoding": self.encoding,
            "write_header": True,
            "mode": "w",
        })

        if not data:
            return FileResult(success=False, error="No data to write")

        try:
            self._ensure_dir(file_path)

            columns = list(data[0].keys())

            with open(file_path, opts["mode"], newline='', encoding=opts["encoding"]) as f:
                writer = csv.writer(f, delimiter=opts["delimiter"])

                # 写入表头
                if opts["write_header"]:
                    writer.writerow(columns)

                # 写入数据
                for row in data:
                    writer.writerow([row.get(col, "") for col in columns])

                row_count = len(data)

            logger.info(f"[CSV] Wrote {row_count} rows to {file_path}")

            return FileResult(
                success=True,
                output_path=file_path,
                row_count=row_count,
                columns=columns,
            )

        except Exception as e:
            logger.error(f"[CSV] Write failed: {e}")
            return FileResult(success=False, error=str(e))
