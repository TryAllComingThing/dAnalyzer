---
name: query export
description: 将查询结果导出为文件 (CSV/Excel/JSON)
trigger: query export
related_skills:
  - data-query
  - security
  - compliance
---

# /query export - 数据导出

## 功能说明

将查询结果导出为指定格式的文件，支持 CSV、Excel、JSON 等格式。

## 使用方式

```
/query export <格式> <文件名> [SQL查询]
```

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| 格式 | 是 | csv / excel / json / txt |
| 文件名 | 是 | 导出的文件名 (不含扩展名) |
| SQL查询 | 否 | 完整 SQL 语句，为空则导出上次查询结果 |

## 格式支持

| 格式 | 扩展名 | 适用场景 |
|------|--------|----------|
| csv | .csv | 大数据量、通用格式 |
| excel | .xlsx | 需要格式化、多Sheet |
| json | .json | 程序对接、API |
| txt | .txt | 简单文本、日志 |

## 使用示例

### 直接导出

```bash
# 导出为 CSV
/query export csv sales_2026

# 导出为 Excel
/query export excel sales_2026

# 导出为 JSON
/query export json orders_2026
```

### 带查询导出

```bash
# 导出 SQL 结果到 CSV
/query export csv result SELECT * FROM sales WHERE date > '2026-04-01'

# 导出 SQL 结果到 Excel (多Sheet)
/query export excel monthly_report SELECT month, SUM(amount) FROM sales GROUP BY month

# 导出自然语言查询结果
/query export csv q1_sales 本月销售额
```

### 导出选项

```bash
# 指定分隔符 (CSV)
/query export csv data --delimiter ;

# 包含表头 (CSV, 默认)
//query export csv data --header

# 不包含表头
/query export csv data --no-header

# 压缩导出 (大文件)
//query export csv large_data --zip
```

## 输出示例

```
用户输入: /query export csv sales_april

执行中...
✓ 查询完成: 10,000 行

导出中...
✓ 导出完成: sales_april.csv (2.3MB)

📁 文件位置: /downloads/sales_april.csv
```

## 自动处理

1. **结果校验**: 检查数据量是否超出限制
2. **安全检查**: 自动脱敏 + 合规检查
3. **格式转换**: 编码转换 (UTF-8)
4. **文件压缩**: 大文件自动压缩

## 限制说明

| 类型 | 限制 | 说明 |
|------|------|------|
| 单次导出 | 100万行 | 超出自动分片 |
| 文件大小 | 100MB | 超出自动压缩 |
| 列数 | 100列 | 超出提示 |

## 合规检查

导出前自动检查:
- ✅ 身份证号脱敏
- ✅ 手机号脱敏
- ✅ 银行卡号脱敏
- ✅ 邮箱脱敏
- ✅ 权限验证

## 相关命令

- `/query sql` - SQL 直接查询
- `/query nl` - 自然语言查询
- `/help query` - 返回查询命令列表
