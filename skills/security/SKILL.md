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

## 执行指令

**所有数据输出前必须调用 `python scripts/security_scan.py` 进行安全扫描，禁止跳过。**

```bash
# 基础用法：从 stdin 输入数据，输出扫描结果
echo '[{"name": "张三", "phone": "13812345678"}]' | python scripts/security_scan.py

# 从文件读取，保存脱敏后的数据到文件
python scripts/security_scan.py --input data/output.json --output data/cleaned.json

# 仅检查不输出脱敏数据
python scripts/security_scan.py --check-only --input data/output.json

# 显示详细扫描信息
python scripts/security_scan.py --input data/output.json --verbose
```

脚本返回 JSON：
```json
{"pass": true, "level": "HIGH", "blocked": [], "masked": ["phone", "name"], "clean_data": [...]}
```

**P0 命中时退出码为 2**，数据被拦截，必须向用户提示并移除敏感字段后重新扫描。

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



## 依赖

- **规则**: rules/legal/data-security.md, rules/legal/privacy-protection.md
- **子技能**: sensitive-detection.md, masking-rules.md, pii-detection.md, compliance-check.md, masking-engine.md, sensitive-desensitize.md, audit-log-gen.md
- **合规清单**: references/compliance-checklist.md
