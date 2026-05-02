---
name: model
description: 数据建模方法参考 — 归因分析、聚类、RFM、预测、漏斗等
---

# 数据建模技能 (Model)

> **使用说明**：当前阶段模型执行依托 Claude 通用知识推理，无独立 Python 模型实现。子技能文件为方法参考文档（概念定义 + 执行流程），非可调用模块。

## When to Activate

- Use this skill when performing attribution analysis
- Use this skill when doing clustering or segmentation analysis
- Use this skill when performing RFM analysis
- Use this skill when forecasting trends or predictions

## 方法类型

1. **归因分析** - 多渠道归因、贡献度分析
2. **聚类分析** - 用户分群、行为分组
3. **队列分析** - 用户留存、同期群分析
4. **相关性分析** - 变量关系、影响因素
5. **预测模型** - 趋势预测、销量预测
6. **漏斗模型** - 转化分析、流失分析
7. **RFM模型** - 用户价值分层
8. **趋势分析** - 走势预测、季节性

## 子技能参考文件

| 方法 | 文件 | 内容 |
|------|------|------|
| 归因分析 | references/attribution.md | 多渠道归因框架 |
| 聚类分析 | references/clustering.md | 聚类分析流程 |
| 队列分析 | references/cohort-analysis.md | 同期群分析 |
| 相关性分析 | references/correlation-analysis.md | 变量相关方法 |
| 预测模型 | references/forecasting.md | 预测方法 |
| 漏斗模型 | references/funnel-analysis.md | 转化漏斗 |
| RFM模型 | references/rfm-analysis.md | 用户价值RFM |
| 趋势分析 | references/trend-analysis.md | 走势分析

## 使用场景

### 场景1: 用户分群
```
用户: 按用户行为分群
→ 调用 model 技能 → [REVIEWER: 模型选择] → 用户确认 → 聚类分析
→ 输出用户分群结果
```

### 场景2: 营销归因
```
用户: 分析各渠道贡献度
→ 调用 model 技能 → [REVIEWER: 模型选择] → 归因分析
→ 输出各渠道贡献占比
```

## 执行流程 (Tool Wrapper + Multi-step 模式)

```
[开始] → [REVIEWER: 模型选择器] → [用户确认] → [执行模型] → [REVIEWER: 结果校验] → [输出]
                          ↓ 不确认
                      [重新选择]
```

### 详细步骤

1. **[REVIEWER] 模型选择器 (Auto-Selection)**
   - 分析输入数据特征（数据量、字段类型、业务场景）
   - 根据 `references/model-selection-rules.md` 规则推荐最佳模型
   - 输出推荐模型列表及理由

2. **[MULTI-STEP] 用户确认**
   - "推荐使用 [模型名称]，原因：..."
   - 等待用户确认后执行
   - 用户可选择其他模型或调整参数

3. **执行选定的模型**
   - 归因分析 → references/attribution.md
   - 聚类分析 → references/clustering.md
   - 预测模型 → references/forecasting.md
   - 等等

4. **[REVIEWER] 结果校验**
   - 验证模型输出质量
   - 检查指标是否合理
   - **如果结果异常：提示重新选择模型**

5. **输出结果**
   - 模型结果数据
   - 分析报告
   - 建议

## 依赖配置

- skills/data-query - 数据查询
- skills/data-clean - 数据清洗
- connectors/datawarehouse/ - 数仓连接
