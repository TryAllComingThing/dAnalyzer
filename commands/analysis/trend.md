---
name: analysis trend
description: 时间趋势分析，支持日/周/月/季/同比/环比
trigger: analysis trend
related_skills:
  - data-analysis
  - visual
---

# /analysis trend - 趋势分析

## 功能说明

对时间序列数据进行趋势分析，包括:
- 日/周/月趋势
- 同比分析 (YoY)
- 环比分析 (MoM)
- 异常检测

## 使用方式

```
/analysis trend <指标> [--granularity=<粒度>] [--compare=<对比类型>]
```

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| 指标 | 是 | 分析的指标，如"销售额"、"用户数" |
| --granularity | 否 | 时间粒度: day/week/month/quarter/year |
| --compare | 否 | 对比类型: yoy (同比) / mom (环比) |

## 使用示例

### 基本趋势

```bash
# 销售趋势 (日)
/analysis trend 销售额

# 销售趋势 (周)
/analysis trend 销售额 --granularity=week

# 销售趋势 (月)
/analysis trend 销售额 --granularity=month
```

### 对比分析

```bash
# 同比分析
/analysis trend 销售额 --compare=yoy

# 环比分析
/analysis trend 销售额 --compare=mom

# 同比+月粒度
/analysis trend 销售额 --granularity=month --compare=yoy
```

### 指定维度

```bash
# 按地区
/analysis trend 销售额 --dimension=region

# 按产品分类
/analysis trend 销量 --dimension=category
```

## 输出示例

```
📈 销售额趋势分析 (2026年Q1)

┌─────────┬──────────┬────────┬────────┐
│  月份   │   销售额  │  环比   │  同比   │
├─────────┼──────────┼────────┼────────┤
│ 1月    │  1,234万  │   -    │ +15%   │
│ 2月    │  1,456万  │ +18%   │ +22%   │
│ 3月    │  1,789万  │ +23%   │ +28%   │
└─────────┴──────────┴────────┴────────┘

📊 洞察:
• 3月环比增长23%，增长趋势明显
• 同比上涨28%，超过去年同期
• 建议: 继续保持增长势头
```

## 自动处理

1. **时间范围**: 自动识别 (本月/本季/本年)
2. **基准线**: 自动计算均值和趋势线
3. **异常检测**: 识别偏离趋势的异常点
4. **可视化**: 自动生成趋势图表

## 相关命令

- `/analysis rfm` - RFM 用户分析
- `/analysis funnel` - 漏斗分析
- `/query nl` - 数据查询
- `/help analysis` - 返回分析命令列表
