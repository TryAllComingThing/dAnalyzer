# -*- coding: utf-8 -*-
"""File Connector unit tests — CSV, JSON, Excel"""

import pytest
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from connectors.tool.base import FileResult
from connectors.tool.csv_connector import CSVConnector
from connectors.tool.json_connector import JSONConnector


class TestFileResult:
    """FileResult dataclass tests"""

    def test_defaults(self):
        r = FileResult(success=True)
        assert r.success is True
        assert r.output_path is None
        assert r.row_count == 0
        assert r.columns == []
        assert r.raw_data is None
        assert r.error is None

    def test_with_data(self):
        r = FileResult(
            success=True,
            output_path="/tmp/test.csv",
            row_count=100,
            columns=["a", "b"],
            raw_data=[{"a": 1, "b": 2}],
        )
        assert r.row_count == 100
        assert r.columns == ["a", "b"]
        assert r.raw_data == [{"a": 1, "b": 2}]

    def test_error_state(self):
        r = FileResult(success=False, error="File not found")
        assert r.success is False
        assert r.error == "File not found"


class TestCSVConnector:
    """CSVConnector read/write tests"""

    def test_read_basic(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age\nAlice,30\nBob,25\n")

        result = CSVConnector().read(str(csv_file))

        assert result.success is True
        assert result.row_count == 2
        assert result.columns == ["name", "age"]

    def test_read_tsv(self, tmp_path):
        tsv_file = tmp_path / "test.tsv"
        tsv_file.write_text("name\tage\nAlice\t30\nBob\t25\n")

        result = CSVConnector().read(str(tsv_file), delimiter="\t")

        assert result.success is True
        assert result.row_count == 2

    def test_read_no_header(self, tmp_path):
        csv_file = tmp_path / "no_header.csv"
        csv_file.write_text("Alice,30\nBob,25\n")

        result = CSVConnector().read(str(csv_file), has_header=False)

        assert result.success is True
        assert result.row_count == 2
        assert result.columns == ["col_0", "col_1"]

    def test_read_max_rows(self, tmp_path):
        csv_file = tmp_path / "large.csv"
        csv_file.write_text("col\n" + "\n".join(str(i) for i in range(100)))

        result = CSVConnector().read(str(csv_file), max_rows=10)

        assert result.success is True
        assert result.row_count == 10

    def test_read_nonexistent_file(self):
        result = CSVConnector().read("nonexistent.csv")
        assert result.success is False
        assert result.error is not None

    def test_read_empty_file(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")

        result = CSVConnector().read(str(csv_file))
        assert result.success is True
        assert result.row_count == 0

    def test_write_basic(self, tmp_path):
        csv_file = tmp_path / "out.csv"
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]

        result = CSVConnector().write(data, str(csv_file))

        assert result.success is True
        assert result.row_count == 2
        content = csv_file.read_text()
        assert "name,age" in content
        assert "Alice,30" in content

    def test_write_empty_data(self, tmp_path):
        result = CSVConnector().write([], str(tmp_path / "empty.csv"))
        assert result.success is False
        assert "No data to write" in result.error

    def test_write_tsv(self, tmp_path):
        csv_file = tmp_path / "out.tsv"
        data = [{"a": "1", "b": "2"}]

        result = CSVConnector().write(data, str(csv_file), delimiter="\t")

        assert result.success is True
        content = csv_file.read_text()
        assert "a\tb" in content

    def test_custom_delimiter_config(self):
        c = CSVConnector({"delimiter": "|"})
        assert c.delimiter == "|"

    def test_custom_encoding(self, tmp_path):
        csv_file = tmp_path / "utf8.csv"
        csv_file.write_text("name\n测试\n", encoding="utf-8")

        result = CSVConnector({"encoding": "utf-8"}).read(str(csv_file))
        assert result.success is True
        assert result.row_count == 1


class TestJSONConnector:
    """JSONConnector read/write tests"""

    def test_read_array(self, tmp_path):
        json_file = tmp_path / "data.json"
        json_file.write_text('[{"name":"Alice","age":30},{"name":"Bob","age":25}]')

        result = JSONConnector().read(str(json_file))

        assert result.success is True
        assert result.row_count == 2
        assert result.columns == ["name", "age"]
        assert result.raw_data is not None
        assert len(result.raw_data) == 2

    def test_read_object_with_data_key(self, tmp_path):
        json_file = tmp_path / "wrapped.json"
        data = {"data": [{"id": 1}, {"id": 2}], "total": 2}
        json_file.write_text(json.dumps(data))

        result = JSONConnector().read(str(json_file), format="object")

        assert result.success is True
        assert result.row_count == 2

    def test_read_object_with_rows_key(self, tmp_path):
        json_file = tmp_path / "rows.json"
        data = {"rows": [{"id": 1}, {"id": 2}]}
        json_file.write_text(json.dumps(data))

        result = JSONConnector().read(str(json_file), format="object")

        assert result.success is True
        assert result.row_count == 2

    def test_read_single_object(self, tmp_path):
        json_file = tmp_path / "single.json"
        json_file.write_text('{"name":"Alice","age":30}')

        result = JSONConnector().read(str(json_file))

        assert result.success is True
        assert result.row_count == 1
        assert result.raw_data is not None

    def test_read_nonexistent_file(self):
        result = JSONConnector().read("nonexistent.json")
        assert result.success is False
        assert result.error is not None

    def test_write_array(self, tmp_path):
        json_file = tmp_path / "out.json"
        data = [{"name": "Alice"}, {"name": "Bob"}]

        result = JSONConnector().write(data, str(json_file))

        assert result.success is True
        assert result.row_count == 2
        parsed = json.loads(json_file.read_text())
        assert len(parsed) == 2

    def test_write_object_format(self, tmp_path):
        json_file = tmp_path / "out_wrapped.json"
        data = [{"id": 1}, {"id": 2}]

        result = JSONConnector().write(data, str(json_file), format="object")

        assert result.success is True
        parsed = json.loads(json_file.read_text())
        assert "data" in parsed
        assert "total" in parsed
        assert parsed["total"] == 2

    def test_write_empty_data(self, tmp_path):
        result = JSONConnector().write([], str(tmp_path / "empty.json"))
        assert result.success is False

    def test_flatten_nested(self):
        nested = {"user": {"name": "Tom", "age": 30}, "order": {"id": 123}}

        result = JSONConnector().flatten(nested)

        assert result["user_name"] == "Tom"
        assert result["user_age"] == 30
        assert result["order_id"] == 123

    def test_flatten_with_list(self):
        nested = {"tags": ["a", "b"], "name": "test"}

        result = JSONConnector().flatten(nested)

        assert result["name"] == "test"
        assert "tags" in result  # lists are JSON-stringified


class TestExcelConnector:
    """ExcelConnector read/write tests (requires pandas + openpyxl)"""

    @pytest.fixture
    def maybe_skip(self):
        try:
            import pandas
            import openpyxl
        except ImportError:
            pytest.skip("pandas and openpyxl required for Excel tests")

    def test_read_basic(self, maybe_skip, tmp_path):
        import pandas as pd

        excel_file = tmp_path / "test.xlsx"
        df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
        df.to_excel(str(excel_file), index=False)

        from connectors.tool.excel_connector import ExcelConnector

        result = ExcelConnector().read(str(excel_file))

        assert result.success is True
        assert result.row_count == 2
        assert "name" in result.columns

    def test_read_nonexistent_file(self, maybe_skip):
        from connectors.tool.excel_connector import ExcelConnector

        result = ExcelConnector().read("nonexistent.xlsx")
        assert result.success is False

    def test_write_basic(self, maybe_skip, tmp_path):
        from connectors.tool.excel_connector import ExcelConnector

        excel_file = tmp_path / "out.xlsx"
        data = [{"name": "Alice", "score": 95}, {"name": "Bob", "score": 87}]

        result = ExcelConnector().write(data, str(excel_file))

        assert result.success is True
        assert result.row_count == 2

    def test_write_empty_data(self, maybe_skip, tmp_path):
        from connectors.tool.excel_connector import ExcelConnector

        result = ExcelConnector().write([], str(tmp_path / "empty.xlsx"))
        assert result.success is False
        assert "No data to write" in result.error
