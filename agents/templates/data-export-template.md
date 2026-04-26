---
name: data-export-template
description: 数据导出流程模板
type: workflow-template
---

# 数据导出流程模板

## 模板说明

用于标准化的数据导出流程，支持多种格式和渠道

## 适用场景

- 数据导出给业务方
- 数据同步到BI系统
- 数据备份

## 流程步骤

1. **导出参数**
   - 数据来源（数仓/本地文件）
   - 导出格式（CSV/Excel/JSON）
   - 目标位置

2. **数据提取**
   - 调用 skills/query/multi-source-query.md
   - 按条件提取数据

3. **数据校验**
   - 调用 checks/data-quality/data-quality-check.md
   - 字段完整性检查

4. **脱敏处理**
   - 调用 skills/security/sensitive-desensitize.md
   - 按规则脱敏

5. **格式转换**
   - 转换为目标格式
   - 编码统一为UTF-8

6. **合规扫描**
   - 调用 checks/compliance/compliance-scan.md
   - 输出前最终校验

7. **导出执行**
   - 导出到目标位置
   - 记录导出日志

## 输入参数

- source: 数据来源
- format: 导出格式
- target: 目标位置
- desensitize: 是否脱敏

## 输出结果

- 导出文件
- 导出日志
- 字段说明（可选）

## 依赖

- skills/query/multi-source-query.md
- skills/security/sensitive-desensitize.md
- checks/data-quality/data-quality-check.md
- checks/compliance/compliance-scan.md
