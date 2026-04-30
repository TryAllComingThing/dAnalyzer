---
name: data-clean
description: 数据预处理技能，覆盖数据清洗和数据质量校验。处理空值、异常值、重复值、格式标准化、连续性检测。支持SQL/内存/文件三种模式，根据数据源自动选择最优处理方式
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
| cleaning_rules | object | 清洗规则配置 | ❌ |

---

## 输出结果

清洗结果类型根据模式确定：
- **SQL 模式**：返回清洗后 SQL 字符串及清洗说明
- **内存模式**：返回清洗后数据集 + 清洗统计（填充数/剔除数/去重数）

---

## 质量校验（可选步骤）

清洗完成后，按需执行质量校验。适用于数据源不可靠、涉及关键业务决策、或用户明确要求质量报告的场景。

### 校验维度

| 维度 | 标准 | 处理 |
|------|------|------|
| 空值 | 数值型≥5%预警、关键字段≥1条终止 | 标记并报告 |
| 异常值 | 3σ原则、业务规则 | 标记并报告 |
| 重复值 | 主键重复预警、完全重复去重 | 标记并报告 |
| 连续性 | 日期断层、数值断层 | 标记并报告 |

### 输出

- 质量检查报告（问题清单 + 修复建议）

---

## 与其他 Skills 的协作

### 上游: data-query

```
data-query → 返回数据源信息 → data-clean → 返回清洗后的数据/SQL
```

---

## 注意事项

1. **优先SQL模式**：数据库数据优先使用 SQL 处理
2. **数据安全**：SQL模式需校验SQL安全性
3. **可追溯**：每步操作需记录日志
4. **可回滚**：保留原始数据备份
5. **内存限制**：内存模式需控制数据量，防止 OOM
