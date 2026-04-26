---
name: insight-gen
description: 数据洞察生成技能，自动分析数据并生成业务洞察和建议
---

# 洞察生成技能 (Insight Generation)

## When to Activate

- Use this skill when needing to generate automatic data insights
- Use this skill when analyzing trends, patterns, or anomalies in data
- Use this skill when needing business recommendations based on data
- Use this skill when creating executive summaries or analysis conclusions

## 核心能力

1. **自动洞察发现** - 从数据中自动发现有价值的信息
2. **趋势解读** - 解读数据变化趋势并给出结论
3. **异常标注** - 标注异常数据点并解释原因
4. **对比分析** - 自动进行同比/环比/竞品对比
5. **建议生成** - 基于数据生成业务建议
6. **摘要提取** - 自动生成分析摘要

## 洞察类型

### 1. 趋势洞察

```yaml
insight:
  type: trend
  data:
    metric: sales_amount
    period: 7d
    direction: up
    change: +15.8%
  generation:
    template: "{{metric}}过去{{period}}呈现{{direction}}趋势，增幅{{change}}"
    conclusion: 销售表现良好，呈上升态势
    confidence: high
```

### 2. 异常洞察

```yaml
insight:
  type: anomaly
  data:
    metric: order_count
    timestamp: 2026-04-25
    expected: 1000
    actual: 250
    deviation: -75%
  generation:
    template: "{{metric}}在{{timestamp}}出现异常，{{deviation}}%偏离预期"
    cause: 可能存在系统故障或数据延迟
    confidence: medium
```

### 3. 对比洞察

```yaml
insight:
  type: comparison
  data:
    metric: revenue
    current: 125000
    previous: 100000
    period: 2026-04 vs 2026-03
    change: +25%
  generation:
    template: "{{period}}期间，{{metric}}环比{{change}}"
    conclusion: 增长显著，超出预期
    confidence: high
```

### 4. 构成洞察

```yaml
insight:
  type: composition
  data:
    metric: sales_by_category
    topCategory: 电子产品
    topShare: 45%
    othersShare: 55%
  generation:
    template: "{{topCategory}}占据{{topShare}}市场份额，是主要收入来源"
    conclusion: 业务高度集中，建议关注品类多元化
    confidence: high
```

### 5. 周期洞察

```yaml
insight:
  type: cyclical
  data:
    metric: daily_users
    pattern: weekend_low
    weekdayAvg: 10000
    weekendAvg: 6000
  generation:
    template: "{{metric}}存在明显的周末效应"
    conclusion: 工作日用户活跃度是周末的1.67倍
    confidence: high
```

## 分析方法

### 1. 统计分析

| 方法 | 输出 |
|------|------|
| 描述性统计 | 均值、中位数、标准差、极值 |
| 分布分析 | 正态/偏态、峰值、谷值 |
| 相关性 | 相关系数、关联规则 |
| 回归分析 | 趋势线、预测值 |

### 2. 模式识别

| 方法 | 输出 |
|------|------|
| 时间序列 | 周期、趋势、季节性 |
| 聚类分析 | 用户分群、行为模式 |
| 异常检测 | 离群点、异常值 |

### 3. 对比分析

| 方法 | 输出 |
|------|------|
| 同比 | 同期对比 |
| 环比 | 周期对比 |
| 目标对比 | 目标完成率 |
| 竞品对比 | 市场对比 |

## 洞察质量评估

```yaml
quality:
  criteria:
    - name: 可信度
      weight: 0.3
      metrics: [数据完整性, 样本量, 计算准确性]
    - name: 新颖性
      weight: 0.2
      metrics: [信息增益, 意外程度]
    - name: 价值性
      weight: 0.3
      metrics: [业务影响, 决策支持]
    - name: 可解释性
      weight: 0.2
      metrics: [清晰度, 逻辑性]
  minScore: 0.6  # 最低分数阈值
```

## 输出格式

### 1. 结构化洞察

```json
{
  "insights": [
    {
      "id": "ins_001",
      "type": "trend",
      "category": "销售分析",
      "title": "销售增长趋势明显",
      "description": "过去7天销售额呈现上升趋势，增幅15.8%",
      "data": {
        "metric": "sales_amount",
        "change": "+15.8%"
      },
      "conclusion": "销售表现良好，建议继续保持推广力度",
      "confidence": 0.9,
      "priority": "high",
      "actions": [
        {
          "type": "keep_trend",
          "description": "继续保持当前推广策略"
        },
        {
          "type": "investigate",
          "description": "分析增长驱动因素"
        }
      ]
    }
  ]
}
```

### 2. 洞察卡片

```
┌─────────────────────────────────┐
│ 📈 销售增长趋势明显              │
├─────────────────────────────────┤
│ 过去7天销售额上升15.8%          │
│                                  │
│ 💡 建议：继续保持推广力度         │
│                                  │
│ 置信度：90%  优先级：高         │
└─────────────────────────────────┘
```

### 3. 洞察摘要

```markdown
## 今日数据洞察摘要

### 核心发现
1. **销售增长** - 销售额同比增长25%，表现优异
2. **用户活跃** - 周末活跃度下降40%，需关注
3. **异常订单** - 今日退款率异常偏高，需排查

### 业务建议
1. 继续保持A产品的推广策略
2. 考虑针对周末推出优惠活动
3. 排查退款率上升原因

### 关注事项
- ⚠️ 华北区域销售额连续3天下降
- ✅ 转化率创历史新高
```

## 执行流程

```
[开始] → [数据加载] → [多维度分析] → [洞察发现]
    → [质量评估] → [排序过滤] → [格式化输出]
```

### 详细步骤

1. **数据加载**
   - 加载分析所需数据
   - 数据预处理和清洗
   - 计算基础统计指标

2. **多维度分析**
   - 趋势分析
   - 异常检测
   - 对比分析
   - 关联分析

3. **洞察发现**
   - 从分析结果中提取洞察
   - 生成洞察描述
   - 标注置信度

4. **质量评估**
   - 评估洞察质量
   - 过滤低质量洞察
   - 排序优先级

5. **格式化输出**
   - 结构化输出
   - 自然语言摘要
   - 可视化展示

## 依赖配置

- skills/data-query - 数据查询
- skills/data-analysis - 数据分析
- skills/data-clean - 数据清洗
- skills/visual - 可视化
- rules/core/indicator-caliber.md - 指标口径

## 使用场景

### 场景1: 自动生成分析报告
```
用户: 分析本月销售数据
→ 调用 insight-gen 技能
→ 加载销售数据 → 多维度分析 → 发现5个洞察
→ 生成摘要报告 → 输出
```

### 场景2: 实时监控预警
```
系统: 检测到数据异常
→ 调用 insight-gen 技能 → 异常分析
→ 生成异常洞察 → 推送给相关人员
```

### 场景3: 仪表盘洞察展示
```
看板: 展示关键洞察卡片
→ 调用 insight-gen 技能 → 获取Top 3洞察
→ 实时更新 → 显示在仪表盘
```

## 输出

- 结构化洞察列表
- 洞察摘要报告
- 洞察卡片数据
- 洞察时间线
- 行动建议列表

## 注意事项

1. 洞察需基于可靠数据，数据质量影响洞察质量
2. 不同业务场景需要调整洞察发现策略
3. 洞察需要定期评估和优化
4. 敏感数据需要脱敏后分析
