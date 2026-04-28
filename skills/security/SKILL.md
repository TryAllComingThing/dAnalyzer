---
name: security
description: 安全合规守门员 — 所有数据输出的强制安全关卡。敏感数据检测、脱敏处理、PII识别、合规检查、审计日志。
---

# Security — 数据安全守门员

## 定位

**security 是所有数据输出的强制关卡。** AGENTS.md 规定：

```
输出流程: ... → 输出技能 → security → 最终输出
                              ↑
                      脱敏 + 合规检查（强制）
```

**任何未经 security 处理的数据禁止输出给用户。**

---

## 执行前必须读取

```
Read: rules/legal/data-security.md
Read: rules/legal/privacy-protection.md
Read: skills/security/references/compliance-checklist.md
```

---

## 敏感数据检测规则

### P0 — 绝对禁止输出（检测到即终止）

| 类型 | 检测正则 | 字段名匹配 |
|------|---------|-----------|
| 身份证号 | `\d{17}[\dXx]` | id_card, identity, 身份证 |
| 银行卡号 | `\d{16,19}` | bank_card, card_no, 银行卡 |
| 密码/密钥 | `password\|secret\|key\|token\|api_key` | password, secret, token |

### P1 — 必须脱敏后输出

| 类型 | 检测正则 | 脱敏规则 | 示例 |
|------|---------|---------|------|
| 手机号 | `1[3-9]\d{9}` | 保留前3后4，中间4位 `****` | `138****1234` |
| 邮箱 | `[\w.-]+@[\w.-]+` | 保留首字符+`***`+域名 | `z***@example.com` |
| 姓名 | 常见姓氏(2-4字) | 保留姓，名替换为 `*` | `张**` |
| 地址 | 含省/市/区/县/路/街 | 保留省市区，详细替换 `***` | `北京市海淀区***` |

### P2 — 建议脱敏

| 类型 | 规则 |
|------|------|
| IP 地址 | 后两段脱敏 `192.168.**.**` |
| 账号 ID | 保留前4后4，中间 `****` |
| 薪酬/金额 | 具体数字替换为 `****`，保留单位 |

---

## 脱敏执行代码

### Python 脱敏函数

```python
import re

# P0 检测 — 命中任一即终止
P0_PATTERNS = {
    "身份证号": re.compile(r'\d{17}[\dXx]'),
    "银行卡号": re.compile(r'\d{16,19}'),
    "密码字段": re.compile(r'password|secret|key|token|api_key', re.IGNORECASE),
}

# P1 脱敏规则
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

# 字段名 → 脱敏函数映射
FIELD_MASK_MAP = {
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
}
```

### 扫描与脱敏流程

```python
def security_scan(data: list[dict]) -> dict:
    """
    对输出数据执行安全扫描。
    返回: {"pass": bool, "blocked": list[str], "masked": list[str], "clean_data": list[dict]}
    """
    blocked = []
    masked = []

    for row in data:
        for key, value in row.items():
            value_str = str(value) if value else ""

            # Step 1: P0 检测 — 命中立即终止
            for p0_name, p0_re in P0_PATTERNS.items():
                if p0_re.search(value_str) or p0_re.search(key):
                    blocked.append(f"P0-BLOCKED: {p0_name} in field '{key}'")
                    return {"pass": False, "blocked": blocked, "masked": masked, "clean_data": []}

            # Step 2: P1 脱敏
            mask_fn = FIELD_MASK_MAP.get(key) or FIELD_MASK_MAP.get(key.lower(), None)
            if mask_fn:
                row[key] = mask_fn(value_str)
                masked.append(key)

    return {"pass": True, "blocked": blocked, "masked": masked, "clean_data": data}
```

---

## 合规检查清单

**输出前必须逐项确认**:

- [ ] **P0 扫描**: 无身份证号、银行卡号、密码/密钥原始数据
- [ ] **P1 脱敏**: 手机号、邮箱、姓名、地址已脱敏
- [ ] **P2 脱敏**: IP 地址、账号 ID 已处理
- [ ] **数据分级**: 已确认数据级别 (L1-L4)，L3 以上禁止输出
- [ ] **审批确认**: L3 级别数据已获部门负责人审批
- [ ] **审计日志**: 记录操作时间、数据类型、脱敏方式、处理结果

### 响应级别

| 级别 | 触发条件 | 动作 |
|------|---------|------|
| **CRITICAL** | P0 检测命中 | 立即终止，提示用户移除敏感字段 |
| **HIGH** | P1 未脱敏 | 自动脱敏后继续，警告用户 |
| **MEDIUM** | P2 未脱敏 | 自动脱敏后继续，提醒用户 |
| **LOW** | 无敏感数据 | 放行，记录审计日志 |

---

## 执行流程

```
数据到达 security
    │
    ▼
┌─────────────────────────┐
│ 1. P0 敏感数据扫描       │
│    命中 → CRITICAL → 终止 │
└──────────┬──────────────┘
           │ 通过
           ▼
┌─────────────────────────┐
│ 2. P1 脱敏处理           │
│    手机号/姓名/邮箱/地址  │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 3. P2 脱敏处理           │
│    IP/账号ID/薪酬        │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 4. 数据分级检查          │
│    L3+ → 需审批          │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ 5. 审计日志记录          │
│    操作时间/类型/结果     │
└──────────┬──────────────┘
           │
           ▼
      输出脱敏数据
```

---

## 依赖

- **规则**: rules/legal/data-security.md, rules/legal/privacy-protection.md
- **子技能**: sensitive-detection.md, masking-rules.md, pii-detection.md, compliance-check.md, masking-engine.md, sensitive-desensitize.md, audit-log-gen.md
- **合规清单**: references/compliance-checklist.md
