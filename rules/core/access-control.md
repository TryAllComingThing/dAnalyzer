# 访问控制说明

> ⚠️ **注意**：本文件已简化，不再包含权限控制逻辑

## 当前设计

dAnalyzer 采用 **无权限控制** 方案，依赖 Claude Code 的用户上下文：

- 用户 = Claude Code 的使用者本人
- 无需额外的用户认证和角色系统

## 安全机制

数据安全通过 **security 技能** 实现：

| 机制 | 说明 |
|------|------|
| 脱敏处理 | 敏感数据自动脱敏 |
| 合规检查 | 数据输出前合规验证 |
| 审计日志 | 操作记录可追溯 |

## 校验流程

```
用户请求 → 执行分析 → security (脱敏+合规) → 输出
```

## 与旧版本区别

| 旧版本 (已废弃) | 新版本 |
|-----------------|---------|
| 用户角色权限 | 无权限控制 |
| 访问级别 L1-L4 | 通过 security 检查 |
| 导出权限控制 | security 脱敏后导出 |

## 相关文件

- skills/security/SKILL.md - 安全合规技能
- checks/compliance/compliance-scan.md - 合规扫描
- checks/compliance/sensitive-data-scan.md - 敏感数据扫描
