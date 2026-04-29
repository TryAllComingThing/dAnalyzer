"""
dAnalyzer 数据安全扫描脚本

用法:
    cat data.json | python scripts/security_scan.py
    python scripts/security_scan.py --input data.json --output cleaned.json
    python scripts/security_scan.py --check-only --input data.json

被 security SKILL.md 调用，所有数据输出前的强制安全关卡。
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Dict

# ==================== P0 检测模式 ====================
# 命中任一即终止，禁止输出

P0_PATTERNS: Dict[str, re.Pattern] = {
    "身份证号": re.compile(r'\d{17}[\dXx]'),
    "银行卡号": re.compile(r'\d{16,19}'),
    "密码字段": re.compile(r'password|secret|key|token|api_key', re.IGNORECASE),
}


# ==================== P1 脱敏函数 ====================

def mask_phone(text: str) -> str:
    """手机号: 138****1234"""
    return re.sub(r'(1[3-9]\d)\d{4}(\d{4})', r'\1****\2', text)


def mask_email(text: str) -> str:
    """邮箱: z***@example.com"""
    return re.sub(r'([\w.-])[\w.-]*(@[\w.-]+)', r'\1***\2', text)


def mask_id_card(text: str) -> str:
    """身份证: 110101********1234"""
    return re.sub(r'(\d{6})\d{8}(\d{4})', r'\1********\2', text)


def mask_name(text: str) -> str:
    """姓名: 张* / 张**"""
    return re.sub(r'([一-龥])[一-龥]+', r'\1**', text)


def mask_bank_card(text: str) -> str:
    """银行卡: **** **** **** 1234"""
    return re.sub(r'\d{4}\s*\d{4}\s*\d{4}\s*(\d{4})', r'**** **** **** \1', text)


def mask_ip(text: str) -> str:
    """IP 地址: 192.168.**.**"""
    return re.sub(r'(\d{1,3}\.\d{1,3})\.\d{1,3}\.\d{1,3}', r'\1.**.**', text)


# 字段名 → 脱敏函数映射
FIELD_MASK_MAP: Dict[str, callable] = {
    "phone": mask_phone,
    "mobile": mask_phone,
    "手机": mask_phone,
    "手机号": mask_phone,
    "email": mask_email,
    "邮箱": mask_email,
    "name": mask_name,
    "姓名": mask_name,
    "user_name": mask_name,
    "id_card": mask_id_card,
    "身份证": mask_id_card,
    "bank_card": mask_bank_card,
    "银行卡": mask_bank_card,
    "ip": mask_ip,
    "ip_address": mask_ip,
    "IP": mask_ip,
}


# ==================== 扫描引擎 ====================

SecurityResult = Dict[str, any]
"""{
    "pass": bool,
    "level": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
    "blocked": list[str],
    "masked": list[str],
    "clean_data": list[dict]
}"""


def security_scan(data: List[Dict]) -> SecurityResult:
    """
    对输出数据执行安全扫描。

    流程:
        1. 每行每字段执行 P0 检测 — 命中立即终止
        2. 对已知敏感字段执行 P1 脱敏

    Returns:
        {
            "pass": bool,
            "level": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
            "blocked": list[str],
            "masked": list[str],
            "clean_data": list[dict]
        }
    """
    blocked: List[str] = []
    masked: List[str] = []
    clean_data: List[Dict] = []

    for row in data:
        clean_row = dict(row)

        for key, value in row.items():
            value_str = str(value) if value else ""

            # Step 1: P0 检测 — 命中立即终止
            for p0_name, p0_re in P0_PATTERNS.items():
                if p0_re.search(value_str) or p0_re.search(key):
                    blocked.append(f"P0-BLOCKED: {p0_name} in field '{key}'")
                    return {
                        "pass": False,
                        "level": "CRITICAL",
                        "blocked": blocked,
                        "masked": masked,
                        "clean_data": [],
                    }

            # Step 2: P1 脱敏 — 按字段名匹配合适的脱敏函数
            mask_fn = FIELD_MASK_MAP.get(key) or FIELD_MASK_MAP.get(key.lower())
            if mask_fn:
                clean_row[key] = mask_fn(value_str)
                masked.append(key)

        clean_data.append(clean_row)

    # 确定响应级别
    if blocked:
        level = "CRITICAL"
    elif masked:
        level = "HIGH"
    else:
        level = "LOW"

    return {
        "pass": True,
        "level": level,
        "blocked": blocked,
        "masked": masked,
        "clean_data": clean_data,
    }


def main():
    parser = argparse.ArgumentParser(
        description="dAnalyzer 数据安全扫描 — 所有输出的强制安全关卡",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", "-i",
                        help="输入 JSON 文件 (默认从 stdin 读取)")
    parser.add_argument("--output", "-o",
                        help="输出脱敏后的 JSON 文件")
    parser.add_argument("--check-only", action="store_true",
                        help="仅检查不输出脱敏数据")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="显示详细扫描信息")

    args = parser.parse_args()

    # 读取输入数据
    if args.input:
        raw = Path(args.input).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"pass": False, "level": "CRITICAL",
                          "blocked": [f"JSON parse error: {e}"],
                          "masked": [], "clean_data": []},
                         ensure_ascii=False))
        sys.exit(1)

    # 确保是列表
    if isinstance(data, dict):
        data = [data]

    # 执行扫描
    result = security_scan(data)

    if args.verbose:
        print("[SecurityScan] 结果:", file=sys.stderr)
        print(f"  状态: {'通过' if result['pass'] else '拦截'}", file=sys.stderr)
        print(f"  级别: {result['level']}", file=sys.stderr)
        if result["blocked"]:
            print(f"  拦截: {result['blocked']}", file=sys.stderr)
        if result["masked"]:
            print(f"  脱敏: {result['masked']}", file=sys.stderr)

    if args.check_only:
        output = {k: v for k, v in result.items() if k != "clean_data"}
    else:
        output = result

    out_str = json.dumps(output, ensure_ascii=False, indent=2)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_str, encoding="utf-8")
        print(f"[SecurityScan] Results written to {args.output}")
    else:
        print(out_str)

    # 非零退出码表示拦截
    if not result["pass"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
