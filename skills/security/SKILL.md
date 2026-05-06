---
name: security
description: Use when any skill is about to output data to the user — mandatory final gate for all data outputs including PII detection, masking, and compliance checks. Do NOT use for non-data output or inter-skill data passing between internal skills.
---

# Security — 数据安全守门员

## 概述

所有数据输出的强制安全关卡。在输出链路末端执行 — 任何未经 security 处理的数据禁止交付用户。三级敏感数据检测（P0 绝对禁止/P1 必须脱敏/P2 建议脱敏），覆盖身份证、银行卡、手机号、邮箱、姓名、地址、IP 等。通过 `security_scan.py` 脚本统一执行，输出审计日志。

## 何时使用

- **触发:** 任何技能即将向用户输出数据 — 强制关卡
- **触发:** danalyzer-core 输出链自动嵌入 security，无需用户显式触发
- **不要用于:** 非数据输出场景（无结构化数据的代码/文本）
- **不要用于:** 技能间数据传递（仅在最终输出触发，非中间结果）

**security 是所有数据输出的强制关卡。** AGENTS.md 规定：

```
输出流程: ... → 输出技能 → security → 最终输出
                              ↑
                      脱敏 + 合规检查（强制）
```

**任何未经 security 处理的数据禁止输出给用户。**

---

## 核心步骤

1. **接收输出数据** — 从上游技能（visual/report/dashboard/data-query）获取待输出数据
2. **P0 扫描** — 检测身份证号/银行卡号/密码/密钥，命中则立即终止 → 详见「敏感数据检测规则 > P0」
3. **P1 脱敏** — 手机号保留前3后4、邮箱保留首字符+域名、姓名保留姓、地址保留省市区 → 详见「敏感数据检测规则 > P1」
4. **P2 脱敏** — IP 后两段脱敏、账号 ID 保留前4后4 → 详见「敏感数据检测规则 > P2」
5. **合规检查** — 确认数据分级 L1-L4，L3 以上禁止输出 → 详见「合规检查清单」
6. **审计记录** — 记录操作时间、数据类型、脱敏方式、处理结果

---

## 敏感数据检测规则

> 对应 核心步骤 第 2-4 步

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

**所有数据输出前必须调用 `python3 dAnalyzer/scripts/security_scan.py` 进行安全扫描，禁止跳过。**

```bash
# 基础用法：从 stdin 输入数据，输出扫描结果
echo '[{"name": "张三", "phone": "13812345678"}]' | python3 dAnalyzer/scripts/security_scan.py

# 从文件读取，保存脱敏后的数据到文件
python3 dAnalyzer/scripts/security_scan.py --input knowledge/output.json --output knowledge/cleaned.json

# 仅检查不输出脱敏数据
python3 dAnalyzer/scripts/security_scan.py --check-only --input knowledge/output.json

# 显示详细扫描信息
python3 dAnalyzer/scripts/security_scan.py --input knowledge/output.json --verbose
```

脚本返回 JSON：
```json
{"pass": true, "level": "HIGH", "blocked": [], "masked": ["phone", "name"], "clean_data": [...]}
```

**P0 命中时退出码为 2**，数据被拦截，必须向用户提示并移除敏感字段后重新扫描。

---

## 合规检查清单

> 对应 核心步骤 第 5-6 步

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

- **子技能**: references/sensitive-detection.md, references/masking-rules.md, references/pii-detection.md, references/compliance-check.md, references/masking-engine.md, references/desensitize.md, references/audit-log-gen.md
- **合规清单**: references/compliance-checklist.md

---

## 常见借口与纠正

| 借口 | 现实 |
|--------|---------|
| "这个输出里没有敏感数据，不用扫描" | PII 可能隐藏在非明显字段中（如备注/地址列）；强制扫描是唯一保证 |
| "手动检查一下就行，跑脚本太慢" | 人工检查无法可靠匹配正则模式；脚本在毫秒级完成 |
| "数据已经在上游脱敏过了" | 上游脱敏可能不完整或遗漏；security 是最终关卡，必须独立执行 |

## 红线

- **P0 检测命中:** 检测到 P0 级敏感数据（身份证/银行卡/密码/密钥）— 立即中止输出，提示用户移除敏感字段
- **用户要求跳过:** 用户要求绕过安全扫描 — 拒绝；security 是强制关卡，不可绕过
- **重识别风险:** 脱敏数据仍可通过关联重识别 — 评估并升级处理
- **L3 数据未经审批:** L3 级数据输出请求无书面审批记录 — 拦截输出

## 验证

1. 验证扫描已执行：确认 `security_scan.py` 已运行且返回退出码 0（非 2）
2. 验证 P0 通过：确认输出中无原始身份证号、银行卡号或密码/密钥
3. 验证 P1 已脱敏：确认手机号、邮箱、姓名、地址字段均按规则脱敏
4. 验证 P2 已处理：确认 IP 地址（后两段）和账号 ID 按规则处理
5. 验证数据分级：确认数据等级（L1-L4）已确认，L3+ 有书面审批
6. 验证审计追踪：确认操作时间、数据类型、脱敏方式、处理结果均已记录
