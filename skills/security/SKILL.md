---
name: security
description: 安全合规技能，支持敏感数据检测、脱敏处理、PII识别、合规检查、审计日志等
---

# 安全合规技能 (Security)

## When to Activate

- Use this skill when desensitizing or masking sensitive data
- Use this skill when performing compliance checks
- Use this skill when detecting PII (Personally Identifiable Information)
- Use this skill when auditing data for privacy compliance
- Use this skill when generating audit logs
- Use this skill when performing security validation

## 核心能力

1. **敏感数据检测** - 自动识别敏感字段
2. **数据脱敏** - 字段级/文件级脱敏
3. **PII识别** - 个人身份信息识别
4. **脱敏规则** - 多种脱敏方法
5. **合规检查** - 输出合规性验证
6. **审计日志** - 操作审计记录

## 子技能

| 子技能 | 文件 | 说明 |
|--------|------|------|
| 审计日志 | audit-log-gen.md | 生成审计日志 |
| 合规检查 | compliance-check.md | 合规性检查 |
| 脱敏引擎 | masking-engine.md | 脱敏处理引擎 |
| 脱敏规则 | masking-rules.md | 脱敏规则配置 |
| PII检测 | pii-detection.md | 个人身份信息检测 |
| 敏感脱敏 | sensitive-desensitize.md | 敏感数据脱敏 |
| 敏感检测 | sensitive-detection.md | 敏感数据检测 |

## 使用场景

### 场景1: 数据脱敏
```
用户: 把手机号脱敏
→ 调用 security 技能 → 敏感检测 → 脱敏处理
→ 识别敏感字段 → 应用脱敏规则
→ 输出脱敏数据
```

### 场景2: 合规检查
```
用户: 检查这份数据是否合规
→ 调用 security 技能 → 合规检查
→ 扫描敏感信息
→ 输出合规报告
```

## 依赖配置

- rules/legal/sensitive-data.md - 敏感数据规则
- rules/legal/privacy-protection.md - 隐私保护规则
- connectors/desensitization/ - 脱敏工具连接
