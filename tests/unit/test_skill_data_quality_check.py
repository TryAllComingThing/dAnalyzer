"""
data-quality-check Skill 单元测试 — 验证 LLM 正确执行六维度质量评分
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

QUALITY_RULES = """
# 数据质量校验规则

## 六大维度 (权重)

| 维度 | 评分公式 | 权重 |
|------|----------|------|
| 完整性 | (1 - NULL率) × 100 | 25% |
| 一致性 | (1 - 违反率) × 100 | 25% |
| 准确性 | (1 - 超界率) × 100 | 20% |
| 时效性 | (1 - 延迟率) × 100 | 10% |
| 唯一性 | (1 - 重复率) × 100 | 10% |
| 有效性 | (1 - 无效率) × 100 | 10% |

总分 = 各维度得分 × 权重之和

## 评级
≥95 优秀 | 85-94 良好 | 70-84 一般 | <70 不合格

## 输出格式
{"data_source":"...","overall_score":92.5,"overall_rating":"良好",
 "dimensions":[{"name":"...","score":98,"passed":true,"failed_items":[]}],
 "summary":"...","recommendation":"..."}
"""

CASES = [
    SkillTestCase("Q01", "完整数据高分", [
        {"id": 1, "name": "张三", "amount": 100, "date": "2024-01-01", "status": "已完成"},
        {"id": 2, "name": "李四", "amount": 200, "date": "2024-01-02", "status": "已完成"},
        {"id": 3, "name": "王五", "amount": 150, "date": "2024-01-03", "status": "已完成"},
    ], "对以上数据做六维度质量评分, 数据完整无缺失无重复",
     must_contain=["overall_score", "优秀", "dimensions"]),

    SkillTestCase("Q02", "缺失值扣分", [
        {"id": 1, "name": "张三", "amount": 100},
        {"id": 2, "name": None, "amount": 200},
        {"id": 3, "name": "王五", "amount": None},
        {"id": 4, "name": None, "amount": None},
    ], "对以上数据做六维度质量评分, name有2个null, amount有2个null, 共4行",
     must_contain=["overall_score", "完整性", "failed_items"]),

    SkillTestCase("Q03", "重复值扣分", [
        {"id": 1, "name": "张三", "amount": 100},
        {"id": 1, "name": "张三", "amount": 100},
        {"id": 2, "name": "李四", "amount": 200},
        {"id": 1, "name": "张三", "amount": 100},
    ], "对以上数据做六维度质量评分, id=1 重复3次",
     must_contain=["overall_score", "唯一性"]),

    SkillTestCase("Q04", "多问题综合", [
        {"id": 1, "name": "张三", "amount": 100, "date": "2024-01-01"},
        {"id": 2, "name": None, "amount": -9999, "date": "invalid"},
        {"id": 1, "name": "张三", "amount": 100, "date": "2024-01-01"},
        {"id": 3, "name": "王五", "amount": 100, "date": "2099-01-01"},
    ], "对以上数据做六维度质量评分, 存在缺失+重复+异常值+日期异常",
     must_contain=["overall_score", "dimensions"]),
]

harness = SkillTestHarness(
    "data-quality-check", QUALITY_RULES, CASES, "质量校验任务",
    '{"id":"Q01","data_source":"...","overall_score":0,"overall_rating":"...","dimensions":[...],"summary":"...","recommendation":"..."}',
    batch_size=1, timeout=300,
)

if __name__ == "__main__":
    sys.exit(harness.run())
