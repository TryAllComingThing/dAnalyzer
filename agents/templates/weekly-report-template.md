---
name: weekly-report-template
description: 周报流程模板
type: workflow-template
---

# 周报流程模板

## 流程用途

按业务线自动生成周报，可直接复用，仅需替换业务参数

## 执行时长

5-10分钟

## 执行模式

全串行

## 模板参数

| 参数 | 说明 | 示例 |
|------|------|------|
| ${business_line} | 业务线 | 电商、线下、团购 |
| ${week} | 周次 | 2026年第17周 |
| ${start_date} | 开始日期 | 2026-04-21 |
| ${end_date} | 结束日期 | 2026-04-27 |

## 执行步骤

### 第1步：取数
- 取本周核心指标数据
- 取上周同期数据
- 取去年同比数据

### 第2步：清洗
- 空值处理
- 异常值处理
- 格式标准化

### 第3步：统计
- 计算核心指标
- 计算环比变化
- 计算同比变化

### 第4步：可视化
- 生成趋势图表
- 生成对比图表

### 第5步：报告生成
- 填充周报模板
- 整合图表
- 添加分析结论

### 第6步：脱敏处理
- 敏感数据扫描
- 自动脱敏

### 第7步：合规校验
- 输出合规检查

### 第8步：归档
- 归档周报文件
- 归档图表
- 记录日志

## 调用资源

- skills/report/weekly-report.md
- skills/query/multi-source-query.md
- skills/data-clean/null-abnormal-clean.md
- skills/visual/chart-standard.md
- skills/security/sensitive-desensitize.md
- data/template/report-template.md
- data/indicator/core-indicator-dict.md

## 输出结果

- 周报文件：${business_line}_周报_${week}.md
- 图表文件
- 执行日志
