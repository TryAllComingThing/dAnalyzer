"""
Python Connector

参考: connectors/tool/python-connector.md
"""

import os
import sys
import subprocess
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from .base import BaseFileConnector, FileResult


logger = logging.getLogger(__name__)


class PythonConnector(BaseFileConnector):
    """Python脚本执行连接器"""

    connector_name = "python"

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.python_path = self.config.get("python_path", "python")

    def read(self, file_path: str, **kwargs) -> FileResult:
        """
        读取Python脚本并返回其内容（不执行）

        Args:
            file_path: 脚本路径
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            logger.info(f"[Python] Read script: {file_path} ({len(lines)} lines)")

            return FileResult(
                success=True,
                output_path=file_path,
                row_count=len(lines),
                columns=["line_number", "content"],
            )

        except Exception as e:
            logger.error(f"[Python] Read failed: {e}")
            return FileResult(success=False, error=str(e))

    def execute(self, script_path: str, **kwargs) -> FileResult:
        """
        执行Python脚本

        Args:
            script_path: 脚本路径
            args: 命令行参数
            env: 环境变量
            timeout: 超时时间(秒)
            input_file: 输入数据文件
            output_file: 输出数据文件
        """
        opts = self._parse_kwargs(kwargs, {
            "args": [],
            "env": {},
            "timeout": 300,
            "input_file": None,
            "output_file": None,
        })

        try:
            # 构建命令
            cmd = [self.python_path, script_path]
            cmd.extend(opts["args"])

            # 添加输入输出参数
            if opts.get("input_file"):
                cmd.extend(["--input", opts["input_file"]])
            if opts.get("output_file"):
                cmd.extend(["--output", opts["output_file"]])

            # 构建环境变量
            env = os.environ.copy()
            env.update(opts["env"])

            # 执行
            logger.info(f"[Python] Executing: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=opts["timeout"],
                env=env,
                cwd=os.path.dirname(script_path) or ".",
            )

            if result.returncode != 0:
                error_msg = result.stderr or "Script execution failed"
                logger.error(f"[Python] Error: {error_msg}")
                return FileResult(success=False, error=error_msg)

            # 解析输出
            output = result.stdout.strip()
            row_count = len(output.split('\n')) if output else 0

            logger.info(f"[Python] Script completed, output: {row_count} lines")

            return FileResult(
                success=True,
                output_path=opts.get("output_file"),
                row_count=row_count,
            )

        except subprocess.TimeoutExpired:
            logger.error(f"[Python] Timeout after {opts['timeout']}s")
            return FileResult(success=False, error=f"Timeout after {opts['timeout']}s")
        except Exception as e:
            logger.error(f"[Python] Execution failed: {e}")
            return FileResult(success=False, error=str(e))

    def execute_code(self, code: str, **kwargs) -> FileResult:
        """
        执行Python代码字符串

        Args:
            code: Python代码
            timeout: 超时时间(秒)
        """
        opts = self._parse_kwargs(kwargs, {
            "timeout": 60,
            "globals": None,
        })

        try:
            import pandas as pd

            # 创建执行环境
            exec_globals = {"pd": pd}
            if opts.get("globals"):
                exec_globals.update(opts["globals"])

            # 执行代码
            result = exec(code, exec_globals)

            logger.info("[Python] Code executed successfully")

            return FileResult(
                success=True,
                row_count=1,
            )

        except Exception as e:
            logger.error(f"[Python] Code execution failed: {e}")
            return FileResult(success=False, error=str(e))

    def write(self, data: List[Dict], file_path: str, **kwargs) -> FileResult:
        """此连接器不支持写入操作"""
        return FileResult(success=False, error="Use execute() method instead")
