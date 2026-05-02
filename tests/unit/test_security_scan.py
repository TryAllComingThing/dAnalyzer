"""
security_scan 单元测试 — P0 拦截 / P1 脱敏 / 响应级别

测试 scripts/security_scan.py 的 security_scan() 纯函数.
不依赖 LLM, 纯数据驱动.
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.security_scan import (
    security_scan,
    mask_phone,
    mask_email,
    mask_name,
    mask_ip,
)


class TestP0Blocking:
    """P0 绝对禁止项 — 命中即返回 pass=False, level=CRITICAL"""

    def test_id_card_blocks(self):
        """身份证号检测 → 终止"""
        data = [{"name": "张三", "id_card": "110101199001011234"}]
        r = security_scan(data)
        assert r["pass"] is False
        assert r["level"] == "CRITICAL"
        assert any("身份证号" in b for b in r["blocked"])

    def test_bank_card_blocks(self):
        """银行卡号检测 → 终止"""
        data = [{"card_no": "6222021234567890123"}]
        r = security_scan(data)
        assert r["pass"] is False
        assert r["level"] == "CRITICAL"

    def test_password_field_blocks(self):
        """密码字段名检测 → 终止"""
        data = [{"password": "abc123"}]
        r = security_scan(data)
        assert r["pass"] is False
        assert r["level"] == "CRITICAL"

    def test_token_field_blocks(self):
        """token 字段名检测 → 终止"""
        data = [{"api_key": "sk-abc123"}]
        r = security_scan(data)
        assert r["pass"] is False
        assert r["level"] == "CRITICAL"

    def test_secret_in_value_blocks(self):
        """敏感词在值中 → 终止"""
        data = [{"note": "my password is secret123"}]
        r = security_scan(data)
        assert r["pass"] is False

    def test_p0_blocks_entire_batch(self):
        """P0 命中任意行 → 整批拦截"""
        data = [
            {"name": "正常"},
            {"id_card": "110101199001011234"},  # P0 在第二行
            {"phone": "13812345678"},
        ]
        r = security_scan(data)
        # P0 命中即全量拦截, 不部分通过
        assert r["pass"] is False
        assert r["level"] == "CRITICAL"


class TestP1Masking:
    """P1 必须脱敏 — 命中后自动脱敏继续"""

    def test_phone_mask(self):
        data = [{"phone": "13812345678"}]
        r = security_scan(data)
        assert r["pass"] is True
        assert r["level"] == "HIGH"
        assert r["clean_data"][0]["phone"] == "138****5678"
        assert "phone" in r["masked"]

    def test_email_mask(self):
        data = [{"email": "zhangsan@example.com"}]
        r = security_scan(data)
        assert r["pass"] is True
        assert r["clean_data"][0]["email"] == "z***@example.com"

    def test_name_mask(self):
        data = [{"user_name": "张三丰"}]
        r = security_scan(data)
        assert r["clean_data"][0]["user_name"] in ("张**", "张*")

    def test_multiple_fields_mask(self):
        data = [{"phone": "13900001111", "email": "test@test.com", "name": "李四"}]
        r = security_scan(data)
        assert len(r["masked"]) == 3
        assert r["clean_data"][0]["phone"] == "139****1111"

    def test_non_sensitive_fields_untouched(self):
        data = [{"order_id": "O001", "amount": 100.0, "category": "食品"}]
        r = security_scan(data)
        assert r["level"] == "LOW"
        assert r["clean_data"][0] == data[0]


class TestLevelDetermination:
    """响应级别判定"""

    def test_low_no_sensitive(self):
        r = security_scan([{"a": 1}])
        assert r["level"] == "LOW"
        assert r["pass"] is True

    def test_high_with_p1(self):
        r = security_scan([{"phone": "13812345678"}])
        assert r["level"] == "HIGH"

    def test_critical_with_p0(self):
        r = security_scan([{"password": "x"}])
        assert r["level"] == "CRITICAL"
        assert r["pass"] is False

    def test_p0_clean_data_empty(self):
        """P0 拦截时 clean_data 为空"""
        r = security_scan([{"password": "x"}])
        assert r["clean_data"] == []


class TestEdgeCases:
    """边界情况"""

    def test_empty_list(self):
        r = security_scan([])
        assert r["pass"] is True
        assert r["level"] == "LOW"
        assert r["clean_data"] == []

    def test_none_value(self):
        """None 值不崩溃"""
        data = [{"name": None, "phone": None}]
        r = security_scan(data)
        assert r["pass"] is True

    def test_empty_string(self):
        data = [{"phone": ""}]
        r = security_scan(data)
        assert r["pass"] is True

    def test_mixed_rows(self):
        """多行混合: 部分有敏感字段, 部分没有"""
        data = [
            {"order_id": "O001", "amount": 100},
            {"order_id": "O002", "phone": "13800001111"},
            {"order_id": "O003", "amount": 200},
        ]
        r = security_scan(data)
        assert r["pass"] is True
        assert len(r["clean_data"]) == 3
        # 第一行保持原样
        assert r["clean_data"][0]["order_id"] == "O001"
        # 第二行手机号脱敏
        assert r["clean_data"][1]["phone"] == "138****1111"


class TestMaskFunctions:
    """脱敏函数独立测试"""

    def test_mask_phone_basic(self):
        assert mask_phone("13812345678") == "138****5678"

    def test_mask_phone_in_text(self):
        """文本中的手机号也被脱敏"""
        result = mask_phone("联系 13900001111 获取")
        assert "139****1111" in result

    def test_mask_email_basic(self):
        assert mask_email("admin@company.com") == "a***@company.com"

    def test_mask_name_two_chars(self):
        """两字姓名 → 张**"""
        assert mask_name("张三") == "张**"

    def test_mask_ip_basic(self):
        assert mask_ip("192.168.1.100") == "192.168.**.**"

    def test_mask_ip_local(self):
        assert mask_ip("10.0.0.1") == "10.0.**.**"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
