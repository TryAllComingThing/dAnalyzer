"""
security Skill 单元测试 — 验证 LLM 正确执行敏感数据检测和脱敏规则
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from llm_skill_harness import SkillTestHarness, SkillTestCase

SECURITY_RULES = """
# 安全规则

## P0 绝对禁止输出 (检测到即终止)
身份证号: \\d{17}[\\dXx]
银行卡号: \\d{16,19}
密码/密钥字段: password, secret, key, token

## P1 必须脱敏后输出
手机号: 保留前3后4 → 138****1234
邮箱: 保留首字符+***+域名 → z***@example.com
姓名: 保留姓, 名替换* → 张**

## 脱敏函数
PHONE: re.sub(r'(1[3-9]\\d)\\d{4}(\\d{4})', r'\\1****\\2', text)
EMAIL: re.sub(r'([\\w.-])[\\w.-]*(@[\\w.-]+)', r'\\1***\\2', text)
NAME: re.sub(r'([一-龥])[一-龥]+', r'\\1**', text)
"""

CASES = [
    SkillTestCase("S01", "P0拦截-身份证", [
        {"name": "张三", "id_card": "110101199001011234"},
    ], "扫描数据, 检查是否命中 P0 规则, 命中则拦截",
     must_contain=["拦截", "身份证", "P0"]),

    SkillTestCase("S02", "P1脱敏-手机号", [
        {"user": "U1", "phone": "13812345678"},
        {"user": "U2", "phone": "13900001111"},
    ], "对手机号脱敏: 保留前3后4, 中间替换为****",
     must_contain=["138****5678", "139****1111"]),

    SkillTestCase("S03", "P1脱敏-邮箱姓名", [
        {"name": "张三丰", "email": "zhangsan@company.com"},
    ], "对姓名脱敏(保留姓,名替换*)和对邮箱脱敏(保留首字符+域名)",
     must_contain=["张**", "z***@company.com"]),

    SkillTestCase("S04", "无敏感数据放行", [
        {"order_id": "O001", "amount": 100, "category": "食品"},
    ], "扫描数据, 判断安全级别",
     must_contain=["LOW", "放行"]),
]

harness = SkillTestHarness(
    "security", SECURITY_RULES, CASES, "安全扫描任务",
    '{"id":"S01","pass":true/false,"level":"CRITICAL/HIGH/LOW",'
    '"blocked_fields":[...],"masked_data":[...],"summary":"..."}',
    timeout=180,
)

if __name__ == "__main__":
    sys.exit(harness.run())
