# 漏斗SQL模板

## 电商转化漏斗

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
    '浏览' AS stage, pv AS users, NULL AS rate FROM step1
UNION ALL
SELECT
    '加购' AS stage, cart AS users,
    ROUND(cart * 100.0 / pv, 2) FROM step2, step1
UNION ALL
SELECT
    '下单' AS stage, `order` AS users,
    ROUND(`order` * 100.0 / cart, 2) FROM step3, step2
UNION ALL
SELECT
    '付款' AS stage, payment AS users,
    ROUND(payment * 100.0 / `order`, 2) FROM step4, step3
```

## 注册转化漏斗

```sql
WITH step1 AS (
    SELECT COUNT(DISTINCT user_id) AS register
    FROM user_behavior
    WHERE event = 'register'
      AND dt >= '${start_date}'
),
step2 AS (
    SELECT COUNT(DISTINCT user_id) AS real_name
    FROM user_behavior
    WHERE event = 'real_name'
      AND dt >= '${start_date}'
),
step3 AS (
    SELECT COUNT(DISTINCT user_id) AS bind_card
    FROM user_behavior
    WHERE event = 'bind_card'
      AND dt >= '${start_date}'
),
step4 AS (
    SELECT COUNT(DISTINCT user_id) AS first_order
    FROM user_behavior
    WHERE event = 'first_order'
      AND dt >= '${start_date}'
)
SELECT * FROM step1, step2, step3, step4
```

## 自定义漏斗

```sql
-- 参数：event_list = 'event1,event2,event3'
WITH events AS (
    SELECT
        user_id,
        event,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY dt) AS step
    FROM behavior_log
    WHERE event IN (${event_list})
      AND dt >= '${start_date}'
      AND dt <= '${end_date}'
)
SELECT
    step,
    COUNT(DISTINCT user_id) AS users
FROM events
GROUP BY step
ORDER BY step
```
