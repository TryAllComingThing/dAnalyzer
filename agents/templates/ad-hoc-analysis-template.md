---
name: ad-hoc-analysis-template
description: 临时分析流程模板
type: workflow-template
---

# 临时分析流程模板

## 模板说明

用于一次性临时分析需求，快速响应业务问询

## 适用场景

- 业务方临时数据需求
- 快速查询验证
- 临时问题排查

## 流程步骤

1. **需求接收**
   - 记录业务问题
   - 确认数据范围

2. **快速取数**
   - 调用 skills/query/multi-source-query.md
   - 简化校验流程

3. **数据分析**
   - 基础统计分析
   - 关键结论提取

4. **结果输出**
   - 简要报告形式
   - 直接数据回复

## 特点

- 简化流程，快速响应
- 侧重结论，轻化报告
- 无需归档

## 输入参数

- 业务问题描述
- 所需数据范围
- 期望输出形式

## 输出结果

- 简要分析报告
- 数据明细（可选）
- 后续建议（如有）

## 依赖

- skills/query/multi-source-query.md
- skills/model/trend-analysis.md
