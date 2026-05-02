# 通用SQL模板

## 时间统计模板

### 按日统计模板
```sql
SELECT
    dt,
    COUNT(*) AS cnt,
    SUM(amount) AS total_amount
FROM ${table_name}
WHERE dt >= '${start_date}'
  AND dt <= '${end_date}'
GROUP BY dt
ORDER BY dt
```
- 用途：按天统计
- 参数：table_name, start_date, end_date

### 按周统计模板
```sql
SELECT
    CONCAT(YEAR(dt), '年第', WEEK(dt, 1), '周') AS week,
    COUNT(*) AS cnt,
    SUM(amount) AS total_amount
FROM ${table_name}
WHERE dt >= '${start_date}'
  AND dt <= '${end_date}'
GROUP BY YEAR(dt), WEEK(dt, 1)
ORDER BY week
```
- 用途：按周统计
- 参数：table_name, start_date, end_date

### 按月统计模板
```sql
SELECT
    DATE_FORMAT(dt, '%Y-%m') AS month,
    COUNT(*) AS cnt,
    SUM(amount) AS total_amount
FROM ${table_name}
WHERE dt >= '${start_date}'
  AND dt <= '${end_date}'
GROUP BY DATE_FORMAT(dt, '%Y-%m')
ORDER BY month
```
- 用途：按月统计
- 参数：table_name, start_date, end_date

## 用户分析模板

### 用户分层模板
```sql
SELECT
    user_level,
    COUNT(*) AS user_cnt,
    SUM(order_amount) AS total_amount,
    AVG(order_amount) AS avg_amount
FROM (
    SELECT
        user_id,
        SUM(order_amount) AS order_amount,
        CASE
            WHEN SUM(order_amount) >= 5000 THEN '高价值'
            WHEN SUM(order_amount) >= 1000 THEN '中等价值'
            WHEN SUM(order_amount) >= 100 THEN '低价值'
            ELSE '潜客'
        END AS user_level
    FROM order_info
    WHERE dt >= '${start_date}'
      AND dt <= '${end_date}'
      AND status = 'paid'
    GROUP BY user_id
) t
GROUP BY user_level
ORDER BY total_amount DESC
```
- 用途：用户价值分层
- 参数：start_date, end_date

### 用户留存模板
```sql
WITH new_users AS (
    SELECT user_id, MIN(dt) AS first_dt
    FROM order_info
    WHERE dt >= '${start_date}'
    GROUP BY user_id
),
retention AS (
    SELECT
        DATEDIFF(o.dt, n.first_dt) AS days,
        COUNT(DISTINCT o.user_id) AS user_cnt
    FROM order_info o
    INNER JOIN new_users n ON o.user_id = n.user_id
    WHERE o.dt >= n.first_dt
      AND o.dt <= '${end_date}'
    GROUP BY DATEDIFF(o.dt, n.first_dt)
)
SELECT
    days,
    user_cnt,
    (user_cnt * 100.0 / (SELECT COUNT(*) FROM new_users)) AS retention_rate
FROM retention
WHERE days IN (1, 7, 30)
ORDER BY days
```
- 用途：用户留存分析
- 参数：start_date, end_date

## 转化漏斗模板

### 电商转化漏斗
```sql
WITH step1 AS (
    SELECT COUNT(DISTINCT user_id) AS pv
    FROM behavior_log
    WHERE event = 'page_view'
      AND dt >= '${start_date}'
      AND dt <= '${end_date}'
),
step2 AS (
    SELECT COUNT(DISTINCT user_id) AS cart
    FROM behavior_log
    WHERE event = 'add_cart'
      AND dt >= '${start_date}'
      AND dt <= '${end_date}'
),
step3 AS (
    SELECT COUNT(DISTINCT user_id) AS `order`
    FROM behavior_log
    WHERE event = 'create_order'
      AND dt >= '${start_date}'
      AND dt <= '${end_date}'
),
step4 AS (
    SELECT COUNT(DISTINCT user_id) AS payment
    FROM behavior_log
    WHERE event = 'payment_success'
      AND dt >= '${start_date}'
      AND dt <= '${end_date}'
)
SELECT
    '浏览' AS stage, pv AS user_cnt
    FROM step1
UNION ALL
SELECT
    '加购' AS stage, cart AS user_cnt
    FROM step2
UNION ALL
SELECT
    '下单' AS stage, `order` AS user_cnt
    FROM step3
UNION ALL
SELECT
    '付款' AS stage, payment AS user_cnt
    FROM step4
```
- 用途：电商转化漏斗
- 参数：start_date, end_date
