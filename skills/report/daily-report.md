# 日报生成技能

## 核心功能

按业务线自动生成日报

## 输入参数

- 业务线
- 日期
- 数据文件路径

## 报告结构

1. 标题（业务线+日期）
2. 核心指标（销售额、订单量、客单价）
3. 实时数据（当前销售、今日目标进度）
4. 异常预警（异常指标提醒）
5. 明日关注

## 特点

- 自动化取数
- 实时数据更新
- 异常自动预警
- 适合日常监控

## 调用资源

- assets/template/report-template.md
- assets/indicator/sales-indicator.md
- skills/data-query/SKILL.md
- skills/clean/null-abnormal-clean.md

## 输出结果

- 日报文件（Markdown格式）
- 预警清单
- 执行日志
