---
name: data-quality-check
description: 数据质量校验技能，检测空值、异常值、重复值、数据断层
---

# 数据质量检查技能 (Data Quality Check - REVIEWER)

> **模式**: Reviewer
> 
> 此技能作为Reviewer被其他技能调用，用于校验各环节输出质量

## When to Activate

- Use this skill when checking data quality or performing validation
- Use this skill when performing data quality checks before analysis
- Use this skill when validating null values, outliers, or duplicates
- Use this skill when detecting data continuity issues
- Use this skill when verifying data integrity

## 校验维度

### 1. 空值校验
- 数值型字段：空值占比≥5% → 预警
- 关键字段（销售额、订单量、user_id）：空值≥1条 → 终止

### 2. 异常值校验
- 3σ原则：超出均值±3σ → 标记
- 业务规则：超出合理范围 → 预警

### 3. 重复值校验
- 完全重复：标识并处理
- 主键重复：预警

### 4. 连续性校验
- 日期连续性检查
- 数值断层检测

## 执行流程

1. 数据加载
2. 空值检测
3. 异常值检测
4. 重复值检测
5. 连续性检测
6. 生成质量报告

## 输出结果

- 质量检查报告
- 问题清单
- 修复建议
