# 用户分析SQL模板

## 用户活跃统计
```sql
SELECT
    dt,
    COUNT(DISTINCT user_id) AS active_users,
    COUNT(*) AS actions
FROM user_behavior
WHERE dt >= '${start_date}'
  AND dt <= '${end_date}'
GROUP BY dt
ORDER BY dt
```

## 用户留存分析
```sql
WITH first_login AS (
    SELECT user_id, MIN(dt) AS first_dt
    FROM user_login
    WHERE dt >= '${start_date}'
    GROUP BY user_id
),
retention AS (
    SELECT
        f.first_dt,
        DATEDIFF(l.dt, f.first_dt) AS days,
        COUNT(DISTINCT l.user_id) AS users
    FROM first_login f
    INNER JOIN user_login l ON f.user_id = l.user_id
    WHERE l.dt >= f.first_dt
      AND l.dt <= '${end_date}'
    GROUP BY f.first_dt, DATEDIFF(l.dt, f.first_dt)
)
SELECT
    days,
    SUM(CASE WHEN days = 1 THEN users ELSE 0 END) AS d1,
    SUM(CASE WHEN days = 7 THEN users ELSE 0 END) AS d7,
    SUM(CASE WHEN days = 30 THEN users ELSE 0 END) AS d30
FROM retention
GROUP BY days
```

## 用户价值分层
```sql
SELECT
    user_level,
    COUNT(*) AS user_cnt,
    SUM(order_cnt) AS total_orders,
    SUM(order_amount) AS total_amount,
    AVG(order_amount) AS avg_amount
FROM (
    SELECT
        user_id,
        COUNT(*) AS order_cnt,
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
```

## 用户生命周期
```sql
SELECT
    lifetime,
    COUNT(*) AS user_cnt
FROM (
    SELECT
        user_id,
        DATEDIFF(MAX(dt), MIN(dt)) AS lifetime
    FROM order_info
    GROUP BY user_id
    HAVING COUNT(*) > 1
) t
GROUP BY
    CASE
        WHEN lifetime <= 7 THEN '一周内'
        WHEN lifetime <= 30 THEN '一个月内'
        WHEN lifetime <= 90 THEN '三个月内'
        ELSE '长期'
    END
```
