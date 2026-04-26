---
name: indicator-monitor-template
description: 指标监控流程模板
type: workflow-template
---

# 指标监控流程模板

## 模板说明

用于日常指标监控的标准化流程，可按业务线配置监控指标

## 适用场景

- 日/周/月核心指标监控
- 指标异动预警
- 定期指标通报

## 流程步骤

1. **参数配置**
   - 业务线
   - 监控周期（日/周/月）
   - 监控指标列表

2. **数据取数**
   - 调用 skills/query/multi-source-query.md
   - 按指标取对应数据

3. **指标计算**
   - 计算指标当前值
   - 计算环比/同比变化

4. **阈值校验**
   - 调用 checks/data-quality/data-quality-check.md
   - 检查指标是否超阈值

5. **异动分析**
   - 调用 skills/model/attribution-model.md
   - 分析指标异常原因

6. **报告生成**
   - 生成监控报告
   - 发送预警（如有异常）

## 输入参数

- business_line: 业务线
- period: 监控周期
- indicators: 指标列表（可选，默认核心指标）

## 输出结果

- 监控报告
- 异常预警（如有）
- 趋势图表（可选）

## 依赖

- skills/query/multi-source-query.md
- skills/model/attribution-model.md
- checks/data-quality/data-quality-check.md
- data/indicator/core-indicator-dict.md
