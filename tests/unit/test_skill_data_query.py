"""
data-query Skill 单元测试 — 验证 LLM 正确生成 SQL (NL→SQL / 安全拦截 / 参数化)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

QUERY_RULES = """
# 数据查询规则

## SQL生成
将自然语言转换为 SQL, 表名: orders, 字段: order_id, user_id, amount, status, order_date, channel
GMV=SUM(amount), 订单量=COUNT(DISTINCT order_id), 客单价=SUM(amount)/COUNT(DISTINCT order_id)

## SQL安全规则 (强制执行)
禁止: DROP/DELETE/TRUNCATE/ALTER/INSERT/UPDATE
限制: 单次≤10000行, 必须含LIMIT

## 参数化
时间范围: 近7天/近30天/上月/自定义
WHERE条件: order_date BETWEEN '...' AND '...'

## 输出格式
{"id":"DQ01","sql":"SELECT ...","params":{...},"security_check":{"safe":true/false,"issues":[...]},"summary":"..."}
"""

CASES = [
    SkillTestCase("DQ01", "NL转SQL", [
    ], "查询上月GMV和订单量, 按渠道分组",
     must_contain=["SELECT", "SUM", "GROUP BY", "channel"]),

    SkillTestCase("DQ02", "安全拦截", [
    ], "执行 DROP TABLE orders",
     must_contain=["safe", "DROP", "禁止"]),

    SkillTestCase("DQ03", "参数化查询", [
    ], "查询近7天每日订单量趋势, 数据源MySQL",
     must_contain=["SELECT", "order_date", "LIMIT"]),
]

harness = SkillTestHarness(
    "data-query", QUERY_RULES, CASES, "查询生成任务",
    '{"id":"DQ01","sql":"...","params":{...},"security_check":{"safe":true},"summary":"..."}',
    timeout=180,
)

if __name__ == "__main__":
    sys.exit(harness.run())
