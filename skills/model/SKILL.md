---
name: model
description: 数据建模技能，支持归因分析、聚类分析、趋势预测、RFM模型等
---

# 数据建模技能 (Model)

## When to Activate

- Use this skill when building data models or analytical models
- Use this skill when performing attribution analysis
- Use this skill when doing clustering or segmentation analysis
- Use this skill when creating user personas or user segments
- Use this skill when performing RFM analysis
- Use this skill when forecasting trends or predictions
- Use this skill when analyzing correlations between variables

## 核心能力

1. **归因分析** - 多渠道归因、贡献度分析
2. **聚类分析** - 用户分群、行为分组
3. **队列分析** - 用户留存、同期群分析
4. **相关性分析** - 变量关系、影响因素
5. **预测模型** - 趋势预测、销量预测
6. **漏斗模型** - 转化分析、流失分析
7. **RFM模型** - 用户价值分层
8. **趋势分析** - 走势预测、季节性

## 子技能 (可独立使用)

| 子技能 | 文件 | 说明 |
|--------|------|------|
| 归因分析 | sub-skills/attribution.md | 多渠道归因 |
| 聚类分析 | sub-skills/clustering.md | 用户聚类分群 |
| 队列分析 | cohort-analysis.md | 同期群分析 |
| 相关性分析 | correlation-analysis.md | 变量相关性 |
| 预测模型 | forecasting-model.md | 趋势销量预测 |
| 漏斗模型 | funnel-model.md | 转化漏斗 |
| RFM模型 | rfm-model.md | 用户价值RFM |
| 趋势分析 | trend-analysis.md | 走势分析 |

> **提示**: 子技能可独立调用（如需单独使用归因分析，可直接调用 `model/attribution`）

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
   - 根据 `model-selection-rules.md` 规则推荐最佳模型
   - 输出推荐模型列表及理由

2. **[MULTI-STEP] 用户确认**
   - "推荐使用 [模型名称]，原因：..."
   - 等待用户确认后执行
   - 用户可选择其他模型或调整参数

3. **执行选定的模型**
   - 归因分析 → attribution-model.md
   - 聚类分析 → clustering-model.md
   - 预测模型 → forecasting-model.md
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
