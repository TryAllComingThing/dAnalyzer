# RFM 模型分析

## 核心功能

基于 RFM 模型进行用户价值分层分析。支持两种评分方法，根据数据特征自动选择。

## 模型定义

### R（Recency）— 最近消费时间
- 定义：用户最近一次消费距分析日期的天数
- 计算：分析日期 - 最近消费日期
- 评分：天数越少分数越高

### F（Frequency）— 消费频率
- 定义：统计周期内用户消费次数
- 计算：COUNT(order_id)
- 评分：次数越多分数越高

### M（Monetary）— 消费金额
- 定义：统计周期内用户总消费金额
- 计算：SUM(order_amount)
- 评分：金额越高分数越高

---

## 评分方法

### 方法选择

| 条件 | 推荐方法 | 原因 |
|------|---------|------|
| 有行业标准阈值 | 静态阈值法 | 业务对齐，结果可解释 |
| 数据分布未知 | 分位数法 | 自适应，不依赖行业假设 |
| 数据量 < 1000 | 静态阈值法 | 分位数不稳定 |
| 跨行业通用分析 | 分位数法 | 无需行业配置 |
| 运营团队有明确标准 | 静态阈值法 | 与业务口径一致 |

**默认策略**: 优先使用分位数法（普适性强），用户明确要求时使用静态阈值法。

---

### 方法 A: 分位数分段法（推荐默认）

以 20/40/60/80 分位点为界，自适应数据分布：

```python
import pandas as pd

def rfm_percentile_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    R: 升序排列（天数越少越好）→ 分位数越低分越高
    F: 升序排列（次数越多越好）→ 分位数越高分越高
    M: 升序排列（金额越多越好）→ 分位数越高分越高
    """
    # R: 天数越少分数越高（反向）
    df["r_score"] = pd.qcut(df["recency_days"], q=5, labels=[5, 4, 3, 2, 1])
    # F: 次数越多分数越高（正向）
    df["f_score"] = pd.qcut(df["frequency"], q=5, labels=[1, 2, 3, 4, 5])
    # M: 金额越高分数越高（正向）
    df["m_score"] = pd.qcut(df["monetary"], q=5, labels=[1, 2, 3, 4, 5])

    # 处理重复分位边界（duplicate bins）
    if df["r_score"].isna().any():
        df["r_score"] = pd.qcut(df["recency_days"], q=5, labels=[5, 4, 3, 2, 1], duplicates="drop")
    if df["f_score"].isna().any():
        df["f_score"] = pd.qcut(df["frequency"], q=5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    if df["m_score"].isna().any():
        df["m_score"] = pd.qcut(df["monetary"], q=5, labels=[1, 2, 3, 4, 5], duplicates="drop")

    df["rfm_score"] = df["r_score"].astype(int) + df["f_score"].astype(int) + df["m_score"].astype(int)
    return df
```

**优势**: 自动适应数据分布，不依赖行业经验值。

**注意**: 数据量 < 1000 时分位点不稳定，应降级为静态阈值法。

---

### 方法 B: 静态阈值法（需行业配置）

以下为**电商行业通用阈值**，其他行业需调整：

| 维度 | 1分 | 2分 | 3分 | 4分 | 5分 |
|------|-----|-----|-----|-----|-----|
| R(天) | >180 | 91-180 | 31-90 | 7-30 | ≤7 |
| F(次) | 1 | 2 | 3-5 | 6-10 | >10 |
| M(元) | <100 | 100-500 | 500-1000 | 1000-5000 | >5000 |

**行业阈值参考**:

| 行业 | 高 M 阈值 | 高 F 阈值 | 说明 |
|------|----------|----------|------|
| 电商零售 | >5,000元 | >10次 | 高频低客单价 |
| 金融理财 | >50,000元 | >3次 | 低频高客单价 |
| 汽车房产 | >200,000元 | >1次 | 极低频极高客单价 |
| SaaS/B2B | >10,000元 | >5次 | 中频中客单价 |
| 餐饮外卖 | >500元 | >30次 | 极高频低客单价 |

**静态阈值法 SQL**:

```sql
SELECT
    user_id,
    DATEDIFF('2026-04-28', MAX(order_date)) AS recency_days,
    COUNT(DISTINCT order_id) AS frequency,
    SUM(actual_amount) AS monetary,
    CASE
        WHEN DATEDIFF('2026-04-28', MAX(order_date)) <= 7 THEN 5
        WHEN DATEDIFF('2026-04-28', MAX(order_date)) <= 30 THEN 4
        WHEN DATEDIFF('2026-04-28', MAX(order_date)) <= 90 THEN 3
        WHEN DATEDIFF('2026-04-28', MAX(order_date)) <= 180 THEN 2
        ELSE 1
    END AS r_score,
    CASE
        WHEN COUNT(DISTINCT order_id) > 10 THEN 5
        WHEN COUNT(DISTINCT order_id) >= 6 THEN 4
        WHEN COUNT(DISTINCT order_id) >= 3 THEN 3
        WHEN COUNT(DISTINCT order_id) >= 2 THEN 2
        ELSE 1
    END AS f_score,
    CASE
        WHEN SUM(actual_amount) > 5000 THEN 5
        WHEN SUM(actual_amount) >= 1000 THEN 4
        WHEN SUM(actual_amount) >= 500 THEN 3
        WHEN SUM(actual_amount) >= 100 THEN 2
        ELSE 1
    END AS m_score
FROM orders
WHERE order_date >= '2026-01-01'
GROUP BY user_id
```

---

## 用户分层

| 分层 | R | F | M | 特征 | 运营策略 |
|------|---|---|---|------|----------|
| 高价值用户 | 4-5 | 4-5 | 4-5 | 核心客户，近期活跃高频高消费 | VIP 服务、专属优惠、新品优先 |
| 潜力用户 | 3-5 | 3-5 | 3-5 | 成长客户，有提升空间 | 提升消费频次、交叉销售 |
| 流失风险 | 1-2 | 1-2 | 1-3 | 流失预警，长周期未消费 | 召回策略、大额优惠券 |
| 休眠用户 | 1-2 | 1-2 | 1-2 | 长期未消费，低频低消费 | 唤醒活动、push 触达 |
| 一般用户 | 其余组合 | — | — | 普通客户 | 常规维护 |

### 分层 SQL

```sql
-- 在评分基础上分层
SELECT *,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN '高价值用户'
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN '潜力用户'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 3 THEN '流失风险'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN '休眠用户'
        ELSE '一般用户'
    END AS user_level
FROM rfm_scored
```

---

## 执行流程

1. 提取用户消费数据（时间范围：建议至少 6 个月）
2. 判断评分方法（默认分位数法，用户指定用静态阈值法）
3. 计算 RFM 三个维度值
4. 进行 RFM 评分
5. 用户分层
6. 统计各层级用户数、占比、消费贡献
7. 生成运营建议

## 输出结果

- 用户分层结果表（user_id, r_score, f_score, m_score, user_level）
- 各层级统计（用户数、占比、消费金额、贡献度）
- 运营建议报告

## 依赖

- skills/data-query — 数据提取
- data/model/scoring-model.md — 评分模型参考
