# 时间分析SQL模板

## 按小时统计
```sql
SELECT
    HOUR(create_time) AS hour,
    COUNT(*) AS cnt,
    SUM(amount) AS total_amount
FROM order_info
WHERE DATE(create_time) = '${date}'
GROUP BY HOUR(create_time)
ORDER BY hour
```

## 按天统计
```sql
SELECT
    DATE(create_time) AS dt,
    COUNT(*) AS cnt,
    SUM(amount) AS total_amount
FROM order_info
WHERE create_time >= '${start_date}'
  AND create_time < '${end_date}'
GROUP BY DATE(create_time)
ORDER BY dt
```

## 按周统计
```sql
SELECT
    YEARWEEK(create_time, 1) AS week,
    MIN(DATE(create_time)) AS week_start,
    MAX(DATE(create_time)) AS week_end,
    COUNT(*) AS cnt,
    SUM(amount) AS total_amount
FROM order_info
WHERE create_time >= '${start_date}'
  AND create_time < '${end_date}'
GROUP BY YEARWEEK(create_time, 1)
ORDER BY week
```

## 按月统计
```sql
SELECT
    DATE_FORMAT(create_time, '%Y-%m') AS month,
    COUNT(*) AS cnt,
    SUM(amount) AS total_amount
FROM order_info
WHERE create_time >= '${start_date}'
  AND create_time < '${end_date}'
GROUP BY DATE_FORMAT(create_time, '%Y-%m')
ORDER BY month
```

## 同期对比
```sql
SELECT
    DATE_FORMAT(t1.dt, '%Y-%m-%d') AS dt,
    t1.amount AS current_amount,
    t2.amount AS last_year_amount,
    (t1.amount - t2.amount) / t2.amount AS yoy_growth
FROM (
    SELECT DATE(create_time) AS dt, SUM(amount) AS amount
    FROM order_info
    WHERE create_time >= '${current_start}'
      AND create_time < '${current_end}'
    GROUP BY DATE(create_time)
) t1
LEFT JOIN (
    SELECT DATE(create_time) AS dt, SUM(amount) AS amount
    FROM order_info
    WHERE create_time >= '${last_start}'
      AND create_time < '${last_end}'
    GROUP BY DATE(create_time)
) t2 ON t1.dt = t2.dt
ORDER BY dt
```
