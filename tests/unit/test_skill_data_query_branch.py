"""
data-query 分支逻辑测试 — 验证 LLM 根据数据源类型正确选择 DB→SQL 或 File→Python 路径
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

BRANCH_RULES = """
# 数据查询分支逻辑

## 数据获取执行流程

1. 获取 schema + 判定类型
   python scripts/execute_query.py --datasource <name> --schema
   → 返回 JSON，其中 "type" 字段为 "database" 或 "file"。

2. 分支：
   type = "database" → 生成 SQL → 执行
   type = "file" → 读取全量数据 → Python 分析（不支持 SQL）

## schema 输出示例

数据库:
  {"type": "database", "datasource": "fmcg_orders", "tables": [
    {"name": "orders", "columns": [
      {"name": "order_id", "type": "varchar"}, {"name": "actual_amount", "type": "decimal"},
      {"name": "order_date", "type": "datetime"}, {"name": "channel", "type": "varchar"},
      {"name": "category", "type": "varchar"}]}]}

文件:
  {"type": "file", "datasource": "test_orders", "columns": [
    "order_id", "user_id", "product_name", "category", "actual_amount", "channel", "order_date"]}

## 输出格式 (纯 JSON 一行)
{"id":"B01","datasource_type":"database/file","approach":"SQL/Python","query_or_code":"具体的SQL语句或Python代码片段","summary":"一句话"}
"""

CASES = [
    SkillTestCase("B01", "数据库→生成SQL", [],
        "数据源 type=database, 表 orders(order_id, actual_amount, channel, order_date). 查询各渠道销售额.",
        must_contain=["database", "SQL", "SELECT", "channel", "GROUP BY"]),

    SkillTestCase("B02", "文件→Python分析", [],
        "数据源 type=file, 列 [order_id, product_name, category, actual_amount, channel]. 查询各渠道销售额.",
        must_contain=["file", "Python", "actual_amount"]),

    SkillTestCase("B03", "数据库→复杂SQL", [],
        "数据源 type=database, 表 orders(order_id, actual_amount, order_date, category) 和 users(user_id, city). 查询各城市销售额TOP5.",
        must_contain=["database", "SQL", "JOIN", "GROUP BY", "ORDER BY"]),

    SkillTestCase("B04", "文件→Python聚合", [],
        "数据源 type=file, 列 [user_id, order_count, total_consume, city]. 统计各城市用户数和平均消费.",
        must_contain=["file", "Python", "city"]),
]

harness = SkillTestHarness(
    "data-query-branch", BRANCH_RULES, CASES, "数据查询分支决策任务",
    '{"id":"B01","datasource_type":"database/file","approach":"SQL/Python","query_or_code":"...","summary":"..."}',
    batch_size=1, timeout=180,
)

if __name__ == "__main__":
    sys.exit(harness.run())
