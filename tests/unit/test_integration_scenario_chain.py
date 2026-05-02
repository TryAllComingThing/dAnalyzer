"""
场景串联集成测试 — LLM-injected 多 skill 串联决策验证

覆盖: skill 链编排 / 数据源分支 / SQL 校验恢复 / 数据契约 / 安全脱敏链 / 错误处理
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

CHAIN_RULES = """
# 场景串联规则

## 一、路由层 — 意图分类

| 意图 | 路由目标 | 典型特征 |
|------|----------|----------|
| DATA_DEEP | spawn:danalyzer | 多步清洗/建模/绘图/看板/分析/预测 |
| DATA_SIMPLE | main | 单次查询/简单聚合/取数 |

## 二、复杂度判定

| 请求特征 | 判定 | 处理方式 |
|----------|------|----------|
| 单一查询、无后续处理 | 简单 | 直接 data-query，跳过编排 |
| 查询+1个下游技能(图表/清洗) | 中等 | data-query → 下游技能 |
| >2个技能或有依赖(建模/报告/看板) | 复杂 | 先出 plan，再按链执行 |

## 三、可用技能

data-query, data-clean, data-analysis, model, visual, report, dashboard, insight-gen, security

## 四、数据获取分支逻辑 (data-query SKILL.md)

```
1. 获取 schema + 判定类型
   → type = "database" → 生成 SQL → 校验 → 执行
   → type = "file" → 读取全量数据 → Python 分析（不支持 SQL）
```

分支决策:
- 数据源 type=database → approach=SQL, 生成 SELECT 语句
- 数据源 type=file → approach=Python, 读取 CSV/Excel 后在 Python 中过滤/聚合/排序

## 五、SQL 校验错误恢复链

```
生成 SQL → 静态检查(validate_sql_static)
  → EXPLAIN 校验(validate_sql_explain)
    → 失败 → 根据 error_type 查表处理 → 重生成(最多3次) → 仍失败则中止
```

| error_type | 处理 |
|-----------|------|
| SQL_EMPTY | 检查是否有查询条件未转换 |
| SQL_SYNTAX_ERROR | 修正拼写/括号/关键字 |
| SQL_TABLE_NOT_FOUND | 用 --schema 获取真实表名，重生成 |
| SQL_COLUMN_NOT_FOUND | 用 --schema 获取真实列名，重生成 |
| SQL_FORBIDDEN | 立即中止，不允许写操作 |
| CONNECTION_ERROR | 重试1次，仍失败则告知用户 |

## 六、数据契约 — 技能间统一 JSON 格式

上游输出 → 下游输入:
```json
{"columns": ["col1", "col2"], "rows": [["v1", "v2"]], "row_count": N, "source": "datasource_name"}
```

- data-query 输出此格式
- data-clean 输入此格式，输出同格式
- data-analysis 输入此格式
- 所有中间件保持 columns/rows/row_count 三字段不变

## 七、安全脱敏链 — security 始终在输出链末尾

任何输出链路末尾强制嵌入 security:
```
... → 输出技能 → security → 最终输出
```
禁止绕过 security 直接输出。

## 八、错误处理策略

| 错误 | 策略 | 链是否继续 |
|------|------|-----------|
| 取数超时 | 重试3次(1s→2s→4s) | 成功则继续 |
| 数据为空 | 跳过当前技能，记录警告 | 是 |
| 权限不足 | 中止整个任务 | 否 |
| 规则违规 | 中止整个任务 | 否 |
| SQL校验失败 | 重生成SQL(最多3次) | 成功则继续 |

## 输出格式 (纯 JSON 一行)
{"id":"I01",
 "complexity":"simple/medium/complex",
 "skill_chain":["data-query","data-clean","visual","security"],
 "branch":"database/SQL 或 file/Python",
 "needs_plan":false,
 "error_recovery":"regenerate/abort/skip/retry",
 "summary":"30字以内链路总结"}
"""

CASES = [
    # ══ 完整串联 ══
    SkillTestCase("I01", "4-skill完整链: query→clean→analysis→visual", [],
        "查询上月各渠道销售额，清洗异常值超过3倍标准差的数据，分析各渠道趋势，生成可视化图表。数据源是fmcg_orders数据库。",
        must_contain=["complex", "data-query", "data-clean", "data-analysis", "visual", "security",
                       "database", "SQL"]),

    SkillTestCase("I02", "3-skill链: query→clean→report", [],
        "从test_orders文件查询订单数据，清洗空值和重复行，生成一份数据质量报告。",
        must_contain=["data-query", "data-clean", "report", "file", "Python"]),

    SkillTestCase("I03", "2-skill链: query→model (RFM)", [],
        "查询fmcg_users数据库的用户消费数据，做RFM分群建模。",
        must_contain=["data-query", "model", "database", "SQL"]),

    # ══ 简单单 skill / 中等 ══
    SkillTestCase("I04", "简单单skill: 仅查询", [],
        "查询sys_dept表有多少条记录",
        must_contain=["simple", "data-query"]),

    SkillTestCase("I05", "中等: query→visual", [],
        "查询各渠道订单数并画柱状图",
        must_contain=["data-query", "visual"]),

    # ══ SQL 校验恢复 ══
    SkillTestCase("I06", "SQL校验失败→重生成", [],
        "查询数据库时SQL报错TABLE_NOT_FOUND，应该做什么？",
        must_contain=["regenerate", "schema", "data-query"]),

    SkillTestCase("I07", "SQL写操作→立即中止", [],
        "用户要求在查询中执行DROP TABLE操作",
        must_contain=["abort", "SQL_FORBIDDEN"]),

    # ══ 文件数据源分支 ══
    SkillTestCase("I08", "文件→Python分析(不用SQL)", [],
        "分析test_orders.csv中各品类销量排名，数据源type=file",
        must_contain=["file", "Python"],
        must_not=["SQL", "SELECT"]),

    SkillTestCase("I09", "security始终在链末尾", [],
        "查询用户数据，做清洗和分析，输出结果",
        must_contain=["data-query", "data-clean", "data-analysis", "security"]),

    SkillTestCase("I10", "数据为空→跳过继续", [],
        "查询结果为空时，技能链如何处理？",
        must_contain=["skip", "继续"]),

    SkillTestCase("I11", "权限不足→中止", [],
        "数据库权限不足，技能链如何处理？",
        must_contain=["abort", "中止"]),
]

harness = SkillTestHarness(
    "integration-scenario-chain", CHAIN_RULES, CASES, "场景串联决策任务",
    '{"id":"I01","complexity":"simple/medium/complex","skill_chain":[...],"branch":"database/SQL","needs_plan":false,"error_recovery":"...","summary":"..."}',
    batch_size=1, timeout=180,
)

if __name__ == "__main__":
    sys.exit(harness.run())
