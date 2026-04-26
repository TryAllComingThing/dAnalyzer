---
name: data-clean
description: 数据清洗技能，处理空值、异常值、重复值、格式标准化。支持SQL/内存/文件三种模式，根据数据源自动选择最优处理方式
---

# 数据清洗技能 (Data Clean)

## When to Activate

- Use this skill when cleaning data after retrieval
- Use this skill when handling null values or missing data
- Use this skill when dealing with outliers or abnormal values
- Use this skill when removing duplicate records
- Use this skill when standardizing data formats
- Use this skill when performing data preprocessing

## 处理模式

根据数据源类型自动选择最优处理模式：

| 数据源 | 处理模式 | 推荐程度 |
|--------|----------|----------|
| 数据库 | SQL层处理 | ⭐⭐⭐ 首选 |
| 小文件 (<10万行) | 内存处理 | ⭐⭐ 推荐 |
| 大文件 (≥10万行) | 分块/SQL | ⭐ 谨慎 |

### 模式1: SQL层处理 (数据库数据)

**适用场景**：数据来自 MySQL、ClickHouse、Hive 等数据库

**优势**：
- 性能最优，数据库优化器可以利用索引
- 无需数据传输，直接在引擎层完成
- 可利用数据库的并行处理能力

**执行流程**：
```
1. 分析数据源，生成优化后的清洗 SQL
2. 返回清洗 SQL（供 data-query 执行）
3. 或者直接在当前会话执行清洗 SQL
```

**示例**：
```sql
-- 空值填充 + 异常值处理 + 去重
WITH cleaned AS (
    SELECT
        COALESCE(sales_amount, 0) as sales_amount,
        CASE WHEN sales_amount < 0 THEN NULL ELSE sales_amount END as sales_valid,
        ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY create_time DESC) as rn
    FROM sales_orders
    WHERE dt = '2026-04-25'
)
SELECT * FROM cleaned WHERE rn = 1
```

### 模式2: 内存处理 (小文件)

**适用场景**：CSV、Excel 文件，数据量 < 10万行

**优势**：
- 无需落盘，响应速度快
- 灵活性高，可使用复杂清洗逻辑

**执行流程**：
```
1. 读取文件 → DataFrame
2. 内存中执行清洗逻辑
3. 返回清洗后的 DataFrame
```

**示例**：
```python
# 空值填充
df['sales_amount'].fillna(df['sales_amount'].mean(), inplace=True)

# 异常值处理 (3σ原则)
mean, std = df['sales_amount'].mean(), df['sales_amount'].std()
df = df[(df['sales_amount'] > mean - 3*std) & (df['sales_amount'] < mean + 3*std)]

# 去重
df.drop_duplicates(subset=['order_id'], keep='last', inplace=True)
```

### 模式3: 分块处理 (大文件)

**适用场景**：超大文件，无法一次性加载内存

**策略**：
- 分块读取，分块清洗
- 或转换为临时表，用 SQL 处理

---

## 核心能力

### 1. 空值处理

| 字段类型 | 处理策略 |
|----------|----------|
| 数值型 | 均值/中位数填充 |
| 字符型 | "未知"填充 |
| 日期型 | 向前/向后填充 |
| 关键字段 | 单独标记 |

### 2. 异常值处理

| 检测方法 | 处理方式 |
|----------|----------|
| 3σ原则 | 标记或剔除超出±3σ的值 |
| 业务规则 | 超出合理范围标记预警 |
| 箱线图 | 标记超出1.5倍IQR的值 |

### 3. 重复值处理

| 去重策略 | 说明 |
|----------|------|
| 主键去重 | 按主键去重，保留最新 |
| 完全去重 | 完全重复的行删除 |
| 优先级去重 | 按某字段优先级保留 |

### 4. 格式标准化

| 类型 | 标准化 |
|------|--------|
| 日期 | YYYY-MM-DD |
| 数值 | 保留2位小数 |
| 字符 | 去除首尾空格、统一编码 |
| 手机号 | 统一为11位数字 |

---

## 执行流程

### SQL模式（数据库）

```
[开始] → [分析数据源] → [生成清洗SQL] → [验证SQL] → [返回SQL/执行]
```

1. **分析数据源**：识别数据源类型、字段类型
2. **生成清洗SQL**：根据清洗规则生成优化 SQL
3. **验证SQL**：检查 SQL 安全性（禁止危险操作）
4. **返回SQL**：输出清洗后的 SQL 供 data-query 使用

### 内存模式（文件）

```
[开始] → [读取文件] → [空值处理] → [异常值处理] → [去重] → [格式标准化] → [输出]
```

1. **读取文件**：CSV/Excel → DataFrame
2. **空值处理**：填充/标记
3. **异常值处理**：检测/剔除/标记
4. **去重**：按主键去重
5. **格式标准化**：统一格式
6. **输出**：清洗后的数据

---

## 输入参数

| 参数 | 类型 | 说明 | 必填 |
|------|------|------|------|
| data_source | object | 数据源信息 | ✅ |
| data_source.type | string | database/file | ✅ |
| data_source.path | string | 文件路径（文件模式） | ❌ |
| data_source.table | string | 表名（数据库模式） | ❌ |
| cleaning_rules | object | 清洗规则配置 | ❌ |
| output_mode | string | 输出模式：sql/memory | ❌ |

### 清洗规则配置示例

```yaml
cleaning_rules:
  null_handling:
    sales_amount: mean  # 均值填充
    customer_name: "未知"  # 常量填充
    order_date: forward  # 向前填充
  outlier_handling:
    sales_amount:
      method: 3sigma
      action: remove  # remove/mark/clip
  deduplication:
    key: order_id
    keep: last  # first/last
  format_standardize:
    date: YYYY-MM-DD
    decimal: 2
```

---

## 输出结果

### SQL模式输出

```yaml
output:
  type: sql
  sql: "WITH cleaned AS (...) SELECT * FROM cleaned WHERE rn = 1"
  explanation: "空值填充+异常值处理+去重"
  estimated_rows: 10000
```

### 内存模式输出

```yaml
output:
  type: memory
  data: DataFrame  # 清洗后的数据
  stats:
    total_rows: 10000
    null_filled: 50
    outliers_removed: 30
    duplicates_removed: 10
  report: "清洗报告"
```

---

## 决策逻辑

```python
def select_cleaning_mode(data_source, data_info):
    """
    自动选择最佳清洗模式
    """
    # 模式1: 数据库 → SQL模式
    if data_source.type == "database":
        return {
            "mode": "sql",
            "reason": "数据库数据推荐在SQL层处理，性能最优"
        }

    # 模式2: 小文件 → 内存模式
    if data_source.type == "file" and data_info.get("rows", 0) < 100_000:
        return {
            "mode": "memory",
            "reason": "小文件推荐在内存中处理，速度快"
        }

    # 模式3: 大文件 → 分块处理
    return {
        "mode": "chunked",
        "reason": "大文件建议分块处理或导入临时表"
    }
```

---

## 与其他 Skills 的协作

### 上游: data-query

```
data-query → 返回数据源信息 → data-clean → 返回清洗后的数据/SQL
```

### 下游: data-quality-check

```
data-clean → 清洗后数据 → data-quality-check → 质量验证
```

---

## 依赖配置

- connectors/datawarehouse/* - 数据库连接
- connectors/tool/* - 文件读取
- rules/core/indicator-caliber.md - 指标口径
- data/indicator/* - 指标定义

---

## 注意事项

1. **优先SQL模式**：数据库数据优先使用 SQL 处理
2. **数据安全**：SQL模式需校验SQL安全性
3. **可追溯**：每步操作需记录日志
4. **可回滚**：保留原始数据备份
5. **内存限制**：内存模式需控制数据量，防止 OOM
