"""
data-clean Skill 单元测试 — LLM 注入 SKILL.md 规则 + mock 数据 → 验证清洗行为
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

CLEAN_RULES = """
# 数据清洗规则

## 空值处理
| 字段类型 | 处理策略 |
|----------|----------|
| 数值型 | 均值/中位数填充 |
| 字符型 | "未知"填充 |
| 日期型 | 向前/向后填充 |

## 异常值处理
IQR 法: value < Q1 - 1.5*IQR 或 value > Q3 + 1.5*IQR → 标记异常
3σ原则: 标记或剔除超出±3σ的值

## 重复值处理
按主键去重，保留最新记录

## 格式标准化
日期→YYYY-MM-DD, 手机号→11位数字(去分隔符), 字符→去首尾空格
"""

CASES = [
    SkillTestCase("C01", "空值填充", [
        {"id": 1, "amount": None, "name": "张三", "phone": ""},
        {"id": 2, "amount": "200", "name": None, "phone": "13800138000"},
        {"id": 3, "amount": "300", "name": "李四", "phone": None},
    ], "空值处理: 数值型(amount)用均值填充, 字符型(name,phone)用'未知'填充",
     must_contain=["未知", "250"]),

    SkillTestCase("C02", "去重保留最新", [
        {"order_id": "A1", "amount": "100", "date": "2024-01-01"},
        {"order_id": "A2", "amount": "200", "date": "2024-01-02"},
        {"order_id": "A1", "amount": "150", "date": "2024-01-05"},
        {"order_id": "A3", "amount": "300", "date": "2024-01-03"},
        {"order_id": "A2", "amount": "250", "date": "2024-01-04"},
    ], "按 order_id 去重, 保留日期最晚的记录, 输出3条去重后的记录",
     must_contain=["150", "250", "300"]),

    SkillTestCase("C03", "IQR异常值检测", [
        {"id": 1, "amount": 100},
        {"id": 2, "amount": 110},
        {"id": 3, "amount": 105},
        {"id": 4, "amount": 95},
        {"id": 5, "amount": 9999},
        {"id": 6, "amount": -500},
    ], "用 IQR 法检测 amount 异常值, 标出哪些是异常值",
     must_contain=["9999", "-500"]),

    SkillTestCase("C04", "格式标准化", [
        {"phone": "139-0000-1111", "date": "2024/01/15", "name": " 王五 "},
        {"phone": "13812345678", "date": "01-20-2024", "name": "赵六"},
    ], "手机号去分隔符→11位, 日期→YYYY-MM-DD, 字符去空格",
     must_contain=["13900001111", "2024-01-15", "王五", "2024-01-20"]),
]

harness = SkillTestHarness(
    "data-clean", CLEAN_RULES, CASES, "清洗任务",
    '{"id":"C01","result_data":[...],"stats":{"nulls_filled":2,"duplicates_removed":2},"summary":"..."}',
    timeout=300,
)

if __name__ == "__main__":
    sys.exit(harness.run())
