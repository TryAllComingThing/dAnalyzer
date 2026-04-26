---
name: funnel-analysis
description: 漏斗分析技能，用于分析用户转化路径，识别流失环节，优化转化率。
tools: ["Read", "Bash", "Skill"]
model: sonnet
industry: true
---

# Funnel Analysis Skill

## 核心职责

- 分析用户行为转化路径
- 计算各阶段转化率
- 识别转化瓶颈和流失原因
- 生成漏斗分析报告

## 适用场景

- 用户注册转化分析
- 电商购买漏斗分析
- 营销活动效果分析
- 用户留存分析

## 输入要求

| 字段 | 必填 | 说明 |
|------|------|------|
| funnel_name | 是 | 漏斗名称 |
| steps | 是 | 漏斗步骤列表 |
| start_date | 是 | 开始日期 |
| end_date | 是 | 结束日期 |
| segment | 否 | 用户分群条件 |

## 执行逻辑

### 1. 定义漏斗步骤

```
标准电商漏斗:
1. 访问 (PV/UV)
2. 浏览商品 (view_product)
3. 加购 (add_cart)
4. 下单 (create_order)
5. 支付 (payment)
6. 成交 (completed)
```

### 2. 计算转化指标

```
基础指标:
- 步骤转化率 = (当前步骤用户数 / 上一步骤用户数) × 100%
- 总体转化率 = (当前步骤用户数 / 第一步用户数) × 100%
- 流失率 = 100% - 转化率

高级指标:
- 转化时间 = 用户从第一步到当前步骤的平均时间
- 阶段价值 = 该阶段用户产生的平均收入
```

### 3. 识别问题

```
流失分析:
- 找到转化率最低的步骤
- 分析该步骤的用户特征
- 对比不同用户群体的转化差异
```

## 输出结果

### 标准输出格式

```json
{
  "funnel_name": "电商购买漏斗",
  "date_range": "2026-04-01 ~ 2026-04-30",
  "total_users": 100000,
  "steps": [
    {
      "step": 1,
      "name": "访问",
      "users": 100000,
      "conversion_rate": 100,
      "overall_rate": 100
    },
    {
      "step": 2,
      "name": "浏览商品",
      "users": 65000,
      "conversion_rate": 65,
      "overall_rate": 65,
      "drop_rate": 35
    },
    {
      "step": 3,
      "name": "加购",
      "users": 30000,
      "conversion_rate": 46.2,
      "overall_rate": 30,
      "drop_rate": 53.8
    },
    {
      "step": 4,
      "name": "下单",
      "users": 18000,
      "conversion_rate": 60,
      "overall_rate": 18,
      "drop_rate": 40
    },
    {
      "step": 5,
      "name": "支付",
      "users": 15000,
      "conversion_rate": 83.3,
      "overall_rate": 15,
      "drop_rate": 16.7
    },
    {
      "step": 6,
      "name": "成交",
      "users": 12000,
      "conversion_rate": 80,
      "overall_rate": 12,
      "drop_rate": 20
    }
  ],
  "insights": [
    "从浏览到加购转化率仅46.2%，建议优化商品展示",
    "下单到支付转化率83.3%，支付流程顺畅",
    "整体转化率12%，处于行业中等水平"
  ],
  "recommendations": [
    "优化商品详情页，提升加购率",
    "提供更多支付方式",
    "针对流失较高的步骤进行 A/B 测试"
  ]
}
```

## 与其他技能协同

| 技能 | 协同方式 |
|------|----------|
| data-query | 获取漏斗各阶段数据 |
| data-clean | 清洗异常数据 |
| data-analysis | 深度分析流失原因 |
| visual | 生成漏斗图 |
| report | 生成分析报告 |

## 注意事项

1. 漏斗步骤顺序必须合理
2. 注意时间窗口的选择
3. 区分 UV 和 PV 统计口径
4. 考虑自然流量和推广流量的差异

## 示例查询

```
"分析本月用户注册转化漏斗"
"查看电商首页到下单的转化路径"
"对比新老用户的购买漏斗差异"
```
