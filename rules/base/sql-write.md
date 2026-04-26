# SQL编写规范

## 核心职责

规范SQL编写，提升代码质量和可维护性

## 编码规范

### 关键字规范
- 关键字大写：SELECT、FROM、WHERE、GROUP BY、ORDER BY、HAVING、JOIN、LEFT JOIN、INNER JOIN
- 函数大写：COUNT、SUM、AVG、MAX、MIN、DATE、DATE_FORMAT

### 命名规范
- 表名：小写+下划线
  - 正确：user_order_info、sales_data_2026
  - 错误：userOrderInfo、SalesData
- 字段名：小写+下划线
  - 正确：order_amount、create_time
  - 错误：orderAmount、createTime
- 别名：简短有意义，小写下划线
  - 正确：t1、order_summary
  - 错误：a、temp

### 缩进规范
- 缩进：2或4个空格（统一）
- 换行：每个关键字单独一行
- 对齐：AND/OR条件对齐

## 查询规范

### SELECT规范
```sql
-- 必须指定字段，禁止SELECT *
SELECT
    user_id,
    order_id,
    order_amount,
    create_time
FROM order_info
```

### JOIN规范
```sql
-- 必须指定JOIN类型和条件
SELECT
    t1.user_id,
    t2.user_name
FROM user_info t1
INNER JOIN user_profile t2 ON t1.user_id = t2.user_id
WHERE t1.status = 1

-- 禁止笛卡尔积
```

### WHERE规范
```sql
-- 条件清晰，AND对齐
WHERE
    t1.status = 1
    AND t1.create_time >= '2026-01-01'
    AND t1.create_time < '2026-04-25'
```

### GROUP BY规范
```sql
-- GROUP BY的字段必须包含所有非聚合字段
SELECT
    dt,
    category,
    COUNT(*) AS order_cnt,
    SUM(order_amount) AS total_amount
FROM order_info
GROUP BY dt, category
```

### 子查询规范
```sql
-- 优先使用WITH代替多层嵌套
WITH user_summary AS (
    SELECT
        user_id,
        SUM(order_amount) AS total_amount
    FROM order_info
    GROUP BY user_id
)
SELECT
    u.user_id,
    u.total_amount,
    CASE
        WHEN u.total_amount >= 1000 THEN '高价值'
        ELSE '普通'
    END AS user_level
FROM user_summary u
```

## 性能规范

### 禁止操作
- 禁止SELECT *
- 禁止笛卡尔积
- 禁止在WHERE中使用函数
- 禁止隐式类型转换
- 避免子查询嵌套过深

### 最佳实践
- 使用EXPLAIN分析执行计划
- 创建适当索引
- 分区表按日期分区
- 大数据量分页使用游标

## 注释规范

```sql
-- 注释内容：说明业务逻辑
-- 查询某用户的订单统计
SELECT
    user_id,
    COUNT(*) AS order_cnt,
    SUM(order_amount) AS total_amount
FROM order_info
WHERE user_id = 'U001'
GROUP BY user_id
```

## 校验方式

CLI提醒式校验，仅给出优化建议，不拦截执行

## 建议级别

- 必须遵守：关键字大写、表名小写、禁止SELECT *
- 建议遵守：缩进规范、注释规范、WITH替代子查询
- 性能优化：EXPLAIN分析、索引优化
