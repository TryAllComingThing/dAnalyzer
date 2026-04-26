# SQL样例

## 样本说明

常见SQL查询的样例参考

## 基础查询

```sql
-- 查询订单统计
SELECT
    dt,
    COUNT(*) AS order_cnt,
    SUM(amount) AS total_amount,
    AVG(amount) AS avg_amount
FROM order_info
WHERE dt = '2026-04-24'
  AND status = 'paid'
GROUP BY dt
```

## 复杂查询

```sql
-- 用户消费分层
SELECT
    user_level,
    COUNT(*) AS user_cnt,
    SUM(order_cnt) AS total_orders,
    SUM(amount) AS total_amount
FROM (
    SELECT
        user_id,
        COUNT(*) AS order_cnt,
        SUM(amount) AS amount,
        CASE
            WHEN SUM(amount) >= 5000 THEN '高价值'
            WHEN SUM(amount) >= 1000 THEN '中等价值'
            ELSE '普通'
        END AS user_level
    FROM order_info
    WHERE dt >= '2026-04-01'
      AND dt <= '2026-04-24'
      AND status = 'paid'
    GROUP BY user_id
) t
GROUP BY user_level
```

## 窗口函数

```sql
-- 用户消费排名
SELECT
    user_id,
    amount,
    RANK() OVER (ORDER BY amount DESC) AS rank,
    ROW_NUMBER() OVER (ORDER BY amount DESC) AS row_num,
    DENSE_RANK() OVER (ORDER BY amount DESC) AS dense_rank
FROM (
    SELECT
        user_id,
        SUM(amount) AS amount
    FROM order_info
    WHERE dt >= '2026-04-01'
      AND status = 'paid'
    GROUP BY user_id
) t
```

## 常用模式

- CTE（公共表表达式）
- 条件聚合
- 累计计算
- 移动平均
