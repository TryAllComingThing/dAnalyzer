---
name: monthly-report-template
description: 月报流程模板
type: workflow-template
---

# 月报流程模板

## 流程用途

按业务线自动生成月报，可直接复用，仅需替换业务参数

## 执行时长

10-20分钟

## 执行模式

全串行

## 模板参数

| 参数 | 说明 | 示例 |
|------|------|------|
| ${business_line} | 业务线 | 电商、线下、团购 |
| ${month} | 月份 | 2026年4月 |
| ${start_date} | 开始日期 | 2026-04-01 |
| ${end_date} | 结束日期 | 2026-04-30 |

## 执行步骤

### 第1步：取数
- 取本月核心指标数据
- 取上月数据（环比）
- 取去年同月数据（同比）

### 第2步：多维度取数
- 按渠道维度
- 按商品维度
- 按用户维度

### 第3步：清洗
- 空值处理
- 异常值处理
- 格式标准化

### 第4步：多维度统计
- 核心指标统计
- 渠道分析
- 商品分析
- 用户分析

### 第5步：可视化
- 趋势图表
- 对比图表
- 分布图表

### 第6步：报告生成
- 填充月报模板
- 整合图表
- 添加分析结论

### 第7步：脱敏处理
- 敏感数据扫描
- 自动脱敏

### 第8步：合规校验
- 输出合规检查

### 第9步：归档
- 归档月报文件
- 归档图表
- 记录日志

## 调用资源

- skills/report/monthly-report.md
- skills/query/multi-source-query.md
- skills/data-clean/null-abnormal-clean.md
- skills/model/trend-analysis.md
- skills/visual/chart-standard.md
- skills/security/sensitive-desensitize.md
- data/template/report-template.md
- data/indicator/core-indicator-dict.md

## 输出结果

- 月报文件：${business_line}_月报_${month}.md
- 图表文件
- 数据明细
- 执行日志
