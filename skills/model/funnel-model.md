# 漏斗分析技能

## 核心功能

分析用户从入口到转化的各阶段转化率，识别流失瓶颈。

---

## 漏斗阶段定义

### 电商漏斗（标准）

| 阶段 | 事件 | 说明 |
|------|------|------|
| 1. 浏览 (View) | 访问商品页/首页 | 漏斗入口 |
| 2. 加购 (Cart) | 加入购物车 | 意向信号 |
| 3. 下单 (Order) | 提交订单 | 决策信号 |
| 4. 付款 (Payment) | 完成支付 | 转化终点 |
| 5. 复购 (Repurchase) | 再次购买 | 长期价值 |

### 自定义漏斗示例

| 业务场景 | 阶段定义 |
|---------|---------|
| 注册流程 | 访问 → 注册 → 实名 → 绑卡 → 首次交易 |
| 营销活动 | 曝光 → 点击 → 领券 → 下单 → 核销 |
| 内容产品 | 下载 → 注册 → 首日活跃 → 次日留存 → 订阅 |
| SaaS 试用 | 访问 → 注册 → 激活 → 关键功能使用 → 付费 |

---

## 计算公式

```
阶段转化率 = 当前阶段用户数 / 上一阶段用户数
总体转化率 = 最终阶段用户数 / 第一阶段用户数
流失率 = 1 - 阶段转化率
流失用户数 = 上一阶段用户数 - 当前阶段用户数
平均转化时长 = 当前阶段时间戳 - 上一阶段时间戳（中位数）
```

---

## 分析模式

### 模式 1: 标准漏斗（单周期快照）

适用：查看整体转化健康状况。

```
输出:
┌──────────┐
│ 浏览  1000 │ (100%)
├──────────┤
│ 加购   300 │ (30%)
├──────────┤
│ 下单   120 │ (12%)
├──────────┤
│ 付款   100 │ (10%)
└──────────┘
```

### 模式 2: 趋势型漏斗（时间序列监控）

适用：监控各步骤转化率随时间的变化趋势，识别恶化信号。

```
输出: 折线图 — 每个步骤的转化率按日/周变化
横轴: 时间
纵轴: 各步骤转化率(%)
线条: 加购率、下单率、付款率
```

**预警规则**: 任意步骤转化率连续 3 天下降 15% → 告警。

### 模式 3: 分群漏斗（用户聚类对比）

适用：对比不同用户群的漏斗差异，定位问题人群。

```
分群维度:
├── 新用户 vs 老用户
├── Android vs iOS
├── 付费渠道 vs 自然流量
├── 一线城市 vs 下沉市场
└── 促销期 vs 非促销期
```

**判定**: 同一漏斗步骤，不同分群转化率差异 > 30% → 问题分群。

### 模式 4: 桑基图（Sankey）— 推荐可视化

适用：展示用户从入口到终点的流量流向，直观呈现流失路径。

```
Sankey 配置要点:
- 每个阶段为一个节点列
- 流量宽度 = 用户数
- 流失分支用灰色标注
- 颜色从入口到终点渐深（#E3F2FD → #1565C0）
```

---

## 分析指标

| 指标 | 计算 | 用途 |
|------|------|------|
| 阶段用户数 | COUNT(DISTINCT user_id) per stage | 各阶段独立用户数 |
| 阶段转化率 | stage_N / stage_{N-1} | 单步骤转化效率 |
| 总体转化率 | stage_last / stage_1 | 全链路转化效率 |
| 流失用户数 | stage_{N-1} - stage_N | 流失规模 |
| 流失率 | 1 - 阶段转化率 | 流失严重程度 |
| 平均转化时长 | median(stage_N.time - stage_{N-1}.time) | 转化节奏 |
| 瓶颈指数 | 1 / 阶段转化率（归一化） | 识别最严重瓶颈 |

---

## SQL 查询模板

```sql
WITH funnel AS (
    SELECT
        user_id,
        MAX(CASE WHEN event = 'view' THEN 1 ELSE 0 END) AS reached_view,
        MAX(CASE WHEN event = 'cart' THEN 1 ELSE 0 END) AS reached_cart,
        MAX(CASE WHEN event = 'order' THEN 1 ELSE 0 END) AS reached_order,
        MAX(CASE WHEN event = 'payment' THEN 1 ELSE 0 END) AS reached_payment
    FROM user_events
    WHERE event_date BETWEEN '{start_date}' AND '{end_date}'
    GROUP BY user_id
)
SELECT
    '浏览' AS stage, SUM(reached_view) AS users, 100.0 AS rate FROM funnel
UNION ALL
SELECT '加购', SUM(reached_cart), ROUND(100.0 * SUM(reached_cart) / NULLIF(SUM(reached_view), 0), 1) FROM funnel
UNION ALL
SELECT '下单', SUM(reached_order), ROUND(100.0 * SUM(reached_order) / NULLIF(SUM(reached_cart), 0), 1) FROM funnel
UNION ALL
SELECT '付款', SUM(reached_payment), ROUND(100.0 * SUM(reached_payment) / NULLIF(SUM(reached_order), 0), 1) FROM funnel
```

---

## 执行流程

1. 确定业务场景，定义漏斗阶段和对应事件
2. 选择分析模式（标准/趋势/分群/桑基图）
3. 调用 data-query 提取各阶段用户数据
4. 按用户 ID 关联各阶段
5. 计算转化率和流失率
6. 识别瓶颈阶段（转化率最低 / 流失最多的步骤）
7. 如启用分群模式 → 按维度拆分，对比差异
8. 生成优化建议

---

## 输出结果

- 漏斗数据表（阶段、用户数、转化率、流失率）
- 漏斗图（标准/桑基图，取决于分析模式）
- 趋势图（趋势模式）
- 分群对比表（分群模式）
- 瓶颈分析 + 优化建议
- 流失用户明细（可选）

---

## 应用场景

| 场景 | 推荐模式 |
|------|---------|
| 日常转化健康检查 | 标准漏斗 |
| 转化率持续下降排查 | 趋势型漏斗 |
| 投放渠道效果对比 | 分群漏斗 |
| 产品改版效果评估 | 趋势型漏斗（前后对比） |
| 用户路径优化决策 | 桑基图 |

---

## 依赖

- skills/data-query — 数据提取（使用 funnel-sql-template.md）
- skills/visual — 漏斗图/Sankey/趋势图生成
- skills/data-analysis — 显著性检验（分群对比时）
- data/template/funnel-sql-template.md — SQL 模板
