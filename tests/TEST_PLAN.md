# dAnalyzer Claude Code CLI 测试方案

> 版本: 2.0 (重新设计)
> 创建日期: 2026-04-26
> 测试目标: 通过 Claude Code CLI 测试 dAnalyzer Plugin 数据分析功能

---

## 1 测试架构

### 1.1 测试原理

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Claude Code CLI 测试架构                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐      ┌──────────────────┐      ┌─────────────┐   │
│  │ 测试脚本     │ ───→ │ Claude Code CLI   │ ───→ │ dAnalyzer  │   │
│  │ (Python)    │      │ (claude)          │      │ Plugin     │   │
│  └──────────────┘      └──────────────────┘      └─────────────┘   │
│         │                       │                       │           │
│         │                       │                       │           │
│         │         ┌─────────────┴─────────────┐        │           │
│         │         │   danalyzer-core Agent    │        │           │
│         │         │   + Skills + Rules        │        │           │
│         │         └───────────────────────────┘        │           │
│         │                       │                       │           │
│         │                       ▼                       │           │
│         │              ┌──────────────────┐             │           │
│         │              │ 返回分析结果     │             │           │
│         │              │ (终端输出)       │             │           │
│         │              └────────┬─────────┘             │           │
│         │                       │                       │           │
│         ▼                       ▼                       ▼           │
│  ┌──────────────┐      ┌──────────────────┐      ┌─────────────┐   │
│  │ 验证结果     │      │ 捕获输出内容     │      │ 执行技能    │   │
│  │ (断言)       │      │ (stdout)         │      │ (实际分析)  │   │
│  └──────────────┘      └──────────────────┘      └─────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 测试方式

| 测试方式 | 说明 | 适用场景 |
|----------|------|----------|
| **命令测试** | 通过 `/help`, `/query` 等命令 | 验证命令系统 |
| **技能测试** | 激活 Skills 进行数据分析 | 验证技能功能 |
| **E2E 测试** | 完整用户场景测试 | 验证端到端流程 |

---

## 2 测试场景设计

### 2.1 命令系统测试

| 用例ID | 场景 | 测试命令 | 预期结果 |
|--------|------|----------|-----------|
| CMD-001 | 查看帮助 | `/help` | 显示帮助信息 |
| CMD-002 | 查询帮助 | `/help query` | 显示查询命令 |
| CMD-003 | 分析帮助 | `/help analysis` | 显示分析命令 |
| CMD-004 | 报告帮助 | `/help report` | 显示报告命令 |

### 2.2 数据查询场景

| 用例ID | 场景 | 用户输入 | 预期结果 |
|--------|------|----------|----------|
| QUERY-001 | 简单查询 | "查询最近7天的订单" | 返回订单数据 |
| QUERY-002 | 条件查询 | "查询上海地区销售额超过1000的订单" | 过滤结果 |
| QUERY-003 | 聚合统计 | "统计每个城市的订单数量" | 分组统计 |
| QUERY-004 | 时间范围 | "查询2024年1月的销售数据" | 时间过滤 |

### 2.3 数据清洗场景

| 用例ID | 场景 | 用户输入 | 预期结果 |
|--------|------|----------|----------|
| CLEAN-001 | 空值处理 | "处理数据中的空值" | 空值被填充 |
| CLEAN-002 | 去重 | "去除重复订单" | 重复被去除 |
| CLEAN-003 | 异常值 | "检测并标记异常值" | 异常被标记 |

### 2.4 数据分析场景

| 用例ID | 场景 | 用户输入 | 预期结果 |
|--------|------|----------|----------|
| ANALYSIS-001 | 基础统计 | "统计销售总额" | 返回SUM结果 |
| ANALYSIS-002 | 分组统计 | "按类目统计销售额" | GROUP BY结果 |
| ANALYSIS-003 | 排名分析 | "找出销售额前10的商品" | TOP N结果 |

### 2.5 RFM分析场景

| 用例ID | 场景 | 用户输入 | 预期结果 |
|--------|------|----------|----------|
| RFM-001 | RFM计算 | "进行用户RFM分析" | R/F/M值 |
| RFM-002 | 用户分群 | "按RFM划分用户群体" | 8类分群 |

### 2.6 可视化场景

| 用例ID | 场景 | 用户输入 | 预期结果 |
|--------|------|----------|----------|
| VISUAL-001 | 柱状图 | "生成销售类目柱状图" | 图表生成 |
| VISUAL-002 | 趋势图 | "展示月度销售趋势" | 折线图生成 |

### 2.7 合规安全场景

| 用例ID | 场景 | 用户输入 | 预期结果 |
|--------|------|----------|----------|
| SECURITY-001 | 脱敏 | "导出数据需脱敏" | 手机号/身份证被脱敏 |
| SECURITY-002 | 权限检查 | "检查数据访问权限" | 权限验证结果 |

---

## 3 测试实现

### 3.1 测试项目结构

```
tests/
├── TEST_PLAN.md                 # 本测试方案
├── conftest.py                  # pytest 配置
├── run_tests.py                 # 测试运行脚本
├── data/
│   └── sample/                  # 测试数据
│       ├── test_orders.csv      # 10000行
│       ├── test_users.csv       # 10000行
│       ├── test_products.csv    # 500行
│       └── test_abnormal.csv    # 100行异常
│
├── cli/                         # CLI 交互测试
│   ├── test_command_system.py  # 命令系统测试
│   ├── test_skill_activation.py # 技能激活测试
│   └── test_agent_response.py   # Agent 响应测试
│
├── scenario/                    # 场景测试
│   ├── test_data_query.py       # 数据查询场景
│   ├── test_data_clean.py       # 数据清洗场景
│   ├── test_data_analysis.py    # 数据分析场景
│   ├── test_rfm_analysis.py     # RFM分析场景
│   └── test_visual.py           # 可视化场景
│
└── e2e/                         # 端到端测试
    ├── test_sales_report.py     # 销售周报流程
    └── test_user_rfm.py         # 用户RFM流程
```

### 3.2 测试基类

```python
# tests/cli/base.py
"""
Claude Code CLI 测试基类
通过 subprocess 调用 claude 命令进行测试
"""

import subprocess
import json
import os
import pytest
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")


class ClaudeCodeTester:
    """Claude Code CLI 测试工具"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.test_data_dir = self.project_path / "tests" / "data" / "sample"

    def run_command(self, command: str, timeout: int = 60) -> Dict:
        """
        运行 Claude Code 命令并返回结果

        Args:
            command: 要执行的命令（不含 claude 前缀）
            timeout: 超时时间（秒）

        Returns:
            {"stdout": "...", "stderr": "...", "returncode": 0}
        """
        cmd = [CLAUDE_BIN, command]

        result = subprocess.run(
            cmd,
            cwd=str(self.project_path),
            capture_output=True,
            text=True,
            timeout=timeout,
            input=""  # stdin
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    def send_message(self, message: str, timeout: int = 120) -> Dict:
        """
        发送消息给 Claude Code（对话模式）

        Args:
            message: 用户消息
            timeout: 超时时间

        Returns:
            {"response": "...", "success": bool}
        """
        # 使用 --print 选项获取纯输出
        cmd = [
            CLAUDE_BIN,
            "--print",
            "-p", message
        ]

        result = subprocess.run(
            cmd,
            cwd=str(self.project_path),
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return {
            "response": result.stdout,
            "success": result.returncode == 0,
            "stderr": result.stderr
        }

    def send_message_stream(self, message: str, timeout: int = 120) -> str:
        """
        流式发送消息（实时获取输出）

        Args:
            message: 用户消息
            timeout: 超时时间

        Returns:
            完整响应文本
        """
        cmd = [
            CLAUDE_BIN,
            "-p", message
        ]

        result = subprocess.run(
            cmd,
            cwd=str(self.project_path),
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return result.stdout

    def check_skill_available(self, skill_name: str) -> bool:
        """检查技能是否可用"""
        result = self.run_command("/help")

        # 检查输出中是否包含技能名称
        return skill_name.lower() in result["stdout"].lower()

    def get_test_data_path(self, filename: str) -> Path:
        """获取测试数据路径"""
        return self.test_data_dir / filename


@pytest.fixture
def cli_tester():
    """CLI 测试 fixture"""
    return ClaudeCodeTester(str(PROJECT_ROOT))
```

### 3.3 命令系统测试

```python
# tests/cli/test_command_system.py
"""
命令系统测试
验证 /help, /query, /analysis, /report 等命令
"""

import pytest
from .base import ClaudeCodeTester, PROJECT_ROOT


class TestCommandSystem:
    """命令系统测试"""

    def test_help_command(self, cli_tester):
        """CMD-001: 测试 /help 命令"""
        result = cli_tester.run_command("/help")

        assert result["returncode"] == 0
        assert len(result["stdout"]) > 0
        # 验证包含主要命令分类
        assert "query" in result["stdout"].lower() or "Query" in result["stdout"]

    def test_help_query_command(self, cli_tester):
        """CMD-002: 测试 /help query 命令"""
        result = cli_tester.run_command("/help query")

        assert result["returncode"] == 0
        assert len(result["stdout"]) > 0

    def test_help_analysis_command(self, cli_tester):
        """CMD-003: 测试 /help analysis 命令"""
        result = cli_tester.run_command("/help analysis")

        assert result["returncode"] == 0

    def test_help_report_command(self, cli_tester):
        """CMD-004: 测试 /help report 命令"""
        result = cli_tester.run_command("/help report")

        assert result["returncode"] == 0


class TestSkillActivation:
    """技能激活测试"""

    def test_skill_data_query_available(self, cli_tester):
        """验证 data-query 技能可用"""
        available = cli_tester.check_skill_available("data-query")
        assert available, "data-query 技能应该可用"

    def test_skill_data_clean_available(self, cli_tester):
        """验证 data-clean 技能可用"""
        available = cli_tester.check_skill_available("data-clean")
        assert available, "data-clean 技能应该可用"

    def test_skill_rfm_analysis_available(self, cli_tester):
        """验证 rfm-analysis 技能可用"""
        available = cli_tester.check_skill_available("rfm-analysis")
        assert available, "rfm-analysis 技能应该可用"
```

### 3.4 场景测试

```python
# tests/scenario/test_data_query.py
"""
数据查询场景测试
通过自然语言触发 data-query 技能
"""

import pytest
from tests.cli.base import ClaudeCodeTester, PROJECT_ROOT


class TestDataQueryScenario:
    """数据查询场景测试"""

    @pytest.fixture
    def cli_tester(self):
        return ClaudeCodeTester(str(PROJECT_ROOT))

    def test_simple_query(self, cli_tester):
        """QUERY-001: 简单查询场景"""
        message = "查询最近7天的订单数据"

        response = cli_tester.send_message(message)

        # 验证响应成功
        assert response["success"], f"查询失败: {response.get('stderr')}"

        # 验证返回内容包含数据分析相关关键词
        response_lower = response["response"].lower()
        assert any(keyword in response_lower for keyword in [
            "order", "query", "data", "result", "查询", "订单"
        ]), "响应应该包含数据查询相关内容"

    def test_condition_query(self, cli_tester):
        """QUERY-002: 条件查询场景"""
        message = "查询上海地区销售额超过1000元的订单"

        response = cli_tester.send_message(message)

        assert response["success"]

        # 验证处理了过滤条件
        response_lower = response["response"].lower()
        assert "shanghai" in response_lower or "上海" in response["response"] or \
               "filter" in response_lower or "销售" in response["response"]

    def test_aggregation_query(self, cli_tester):
        """QUERY-003: 聚合统计场景"""
        message = "统计每个城市的订单数量"

        response = cli_tester.send_message(message)

        assert response["success"]

        # 验证进行了聚合计算
        response_lower = response["response"].lower()
        assert any(keyword in response_lower for keyword in [
            "count", "group", "city", "统计", "城市", "聚合"
        ])

    def test_time_range_query(self, cli_tester):
        """QUERY-004: 时间范围查询"""
        message = "查询2024年1月的销售数据"

        response = cli_tester.send_message(message)

        assert response["success"]

        # 验证处理了时间条件
        assert "2024" in response["response"] or "1月" in response["response"] or \
               "january" in response["response"].lower()
```

### 3.5 RFM分析场景测试

```python
# tests/scenario/test_rfm_analysis.py
"""
RFM分析场景测试
"""

import pytest
from tests.cli.base import ClaudeCodeTester, PROJECT_ROOT


class TestRFMAnalysisScenario:
    """RFM分析场景测试"""

    @pytest.fixture
    def cli_tester(self):
        return ClaudeCodeTester(str(PROJECT_ROOT))

    def test_rfm_calculation(self, cli_tester):
        """RFM-001: RFM计算"""
        message = "对我的用户数据进行RFM分析"

        response = cli_tester.send_message(message, timeout=180)

        assert response["success"]

        # 验证返回 RFM 相关内容
        response_lower = response["response"].lower()
        assert any(keyword in response_lower for keyword in [
            "rfm", "recency", "frequency", "monetary",
            "r值", "f值", "m值", "用户分群"
        ])

    def test_user_segmentation(self, cli_tester):
        """RFM-002: 用户分群"""
        message = "将用户按RFM得分划分为不同群体"

        response = cli_tester.send_message(message, timeout=180)

        assert response["success"]

        # 验证包含分群结果
        response_lower = response["response"].lower()
        assert any(keyword in response_lower for keyword in [
            "segment", "高价值", "潜力", "流失", "普通"
        ])
```

### 3.6 E2E端到端测试

```python
# tests/e2e/test_sales_report.py
"""
销售周报端到端测试
验证完整的数据分析流程
"""

import pytest
from tests.cli.base import ClaudeCodeTester, PROJECT_ROOT


class TestSalesReportE2E:
    """销售周报 E2E 测试"""

    @pytest.fixture
    def cli_tester(self):
        return ClaudeCodeTester(str(PROJECT_ROOT))

    def test_complete_flow(self, cli_tester):
        """E2E-001: 完整销售周报流程"""
        # 第一步：查询数据
        message = "查询2024年1月的所有订单数据"

        response = cli_tester.send_message(message, timeout=180)
        assert response["success"]

        # 第二步：数据清洗
        message = "清洗数据，去除空值和重复"

        response = cli_tester.send_message(message, timeout=180)
        assert response["success"]

        # 第三步：数据分析
        message = "统计销售总额、各类目销售额"

        response = cli_tester.send_message(message, timeout=180)
        assert response["success"]

        # 第四步：可视化
        message = "生成销售趋势图"

        response = cli_tester.send_message(message, timeout=180)
        assert response["success"]

    def test_single_request_flow(self, cli_tester):
        """E2E-002: 单次请求完成分析"""
        message = """
        请帮我完成以下任务：
        1. 查询2024年1月的销售数据
        2. 统计每个城市的销售额
        3. 生成柱状图展示
        """

        response = cli_tester.send_message(message, timeout=300)

        # 验证整个流程完成
        assert response["success"]

        # 验证返回了分析结果
        response_lower = response["response"].lower()
        assert len(response["response"]) > 100, "应该返回完整的分析结果"
```

---

## 4 测试数据

### 4.1 测试数据文件

| 文件 | 行数 | 用途 |
|------|------|------|
| test_orders.csv | 10,000 | 订单查询/分析 |
| test_users.csv | 10,000 | 用户RFM分析 |
| test_products.csv | 500 | 商品分析 |
| test_abnormal.csv | 100 | 异常数据测试 |

### 4.2 测试数据导入

测试数据需要先导入到测试数据库：

```sql
-- 创建测试数据库
CREATE DATABASE danalyzer_test;

-- 导入测试数据
LOAD DATA INFILE '/path/to/test_orders.csv'
INTO TABLE test_orders
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;
```

---

## 5 测试执行

### 5.1 执行命令

```bash
# 运行所有测试
pytest tests/ -v

# 仅运行 CLI 测试
pytest tests/cli/ -v

# 仅运行场景测试
pytest tests/scenario/ -v

# 仅运行 E2E 测试
pytest tests/e2e/ -v
```

### 5.2 测试环境要求

```
- Claude Code CLI 已安装
- dAnalyzer Plugin 已配置
- 测试数据库已准备
- 测试数据已导入
```

### 5.3 环境变量

```bash
export CLAUDE_BIN=/Users/kyle/.nvm/versions/node/v22.22.0/bin/claude  # Claude Code 路径
export MYSQL_HOST=localhost               # 数据库地址
export MYSQL_DATABASE=test      # 测试数据库
```

---

## 6 测试用例矩阵

| 类别 | 用例数 | 说明 |
|------|--------|------|
| 命令系统 | 4 | /help 等命令验证 |
| 技能激活 | 3 | 技能可用性验证 |
| 数据查询 | 4 | 查询场景测试 |
| 数据清洗 | 3 | 清洗场景测试 |
| 数据分析 | 3 | 分析场景测试 |
| RFM分析 | 2 | RFM场景测试 |
| 可视化 | 2 | 图表生成测试 |
| E2E | 2 | 端到端流程测试 |
| **总计** | **23** | |

---

## 7 预期结果格式

### 7.1 成功响应

```json
{
  "success": true,
  "response": "分析结果内容...",
  "data_count": 100,
  "processing_time": "2.3s"
}
```

### 7.2 失败响应

```json
{
  "success": false,
  "error": "错误信息",
  "suggestion": "修复建议"
}
```

---

*本文档为 dAnalyzer Claude Code CLI 测试方案 v2.0*

*版本: 2.0*
*更新日期: 2026-04-26*
