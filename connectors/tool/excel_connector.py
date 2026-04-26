"""
Excel Connector

参考: connectors/tool/excel-connector.md
"""

import logging
from typing import List, Dict, Any, Optional
from .base import BaseFileConnector, FileResult


logger = logging.getLogger(__name__)


class ExcelConnector(BaseFileConnector):
    """Excel文件连接器"""

    connector_name = "excel"
    supported_formats = ["xlsx", "xls"]

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)

    def read(self, file_path: str, **kwargs) -> FileResult:
        """
        读取Excel文件

        Args:
            file_path: 文件路径
            sheet_name: 工作表名称 (默认第一个)
            sheet_index: 工作表索引 (默认0)
            header_row: 表头行号 (默认0)
            max_rows: 最大读取行数
        """
        opts = self._parse_kwargs(kwargs, {
            "sheet_name": None,
            "sheet_index": 0,
            "header_row": 0,
            "max_rows": None,
        })

        try:
            import pandas as pd

            # 读取Excel
            df = pd.read_excel(
                file_path,
                sheet_name=opts["sheet_name"] or opts["sheet_index"],
                header=opts["header_row"],
                nrows=opts["max_rows"],
            )

            columns = df.columns.tolist()
            rows = df.values.tolist()
            row_count = len(rows)

            logger.info(f"[Excel] Read {row_count} rows from {file_path}")

            return FileResult(
                success=True,
                output_path=file_path,
                row_count=row_count,
                columns=columns,
            )

        except ImportError:
            logger.error("[Excel] pandas + openpyxl required")
            return FileResult(
                success=False,
                error="pandas and openpyxl required. Install: pip install pandas openpyxl"
            )
        except Exception as e:
            logger.error(f"[Excel] Read failed: {e}")
            return FileResult(success=False, error=str(e))

    def write(self, data: List[Dict], file_path: str, **kwargs) -> FileResult:
        """
        写入Excel文件

        Args:
            data: 数据列表
            file_path: 输出路径
            sheet_name: 工作表名称 (默认Sheet1)
            index: 是否写入索引 (默认False)
            header: 是否写入表头 (默认True)
        """
        opts = self._parse_kwargs(kwargs, {
            "sheet_name": "Sheet1",
            "index": False,
            "header": True,
        })

        if not data:
            return FileResult(success=False, error="No data to write")

        try:
            import pandas as pd

            self._ensure_dir(file_path)

            df = pd.DataFrame(data)

            # 写入Excel (需要openpyxl)
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(
                    writer,
                    sheet_name=opts["sheet_name"],
                    index=opts["index"],
                    header=opts["header"],
                )

            row_count = len(data)
            columns = list(data[0].keys()) if data else []

            logger.info(f"[Excel] Wrote {row_count} rows to {file_path}")

            return FileResult(
                success=True,
                output_path=file_path,
                row_count=row_count,
                columns=columns,
            )

        except ImportError:
            logger.error("[Excel] pandas + openpyxl required")
            return FileResult(
                success=False,
                error="pandas and openpyxl required. Install: pip install pandas openpyxl"
            )
        except Exception as e:
            logger.error(f"[Excel] Write failed: {e}")
            return FileResult(success=False, error=str(e))
