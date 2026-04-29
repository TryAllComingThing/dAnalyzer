# 仪表盘报告技能

## 核心功能

生成数据可视化仪表盘报告，展示核心指标和趋势

## 报告结构

1. **概览区域**
   - 核心KPI卡片
   - 关键指标一览

2. **趋势图表**
   - 调用 skills/visual/（趋势图）
   - 核心指标趋势

3. **占比分析**
   - 调用 skills/visual/（占比图）
   - 维度分布

4. **对比分析**
   - 调用 skills/visual/（对比图）
   - 环比/同比对比

5. **明细数据**
   - 可展开的详细数据表

## 输入参数

- 业务线
- 统计周期
- 展示维度
- 图表类型

## 报告特点

- 交互式图表
- 支持下钻
- 自动刷新
- 响应式布局

## 调用资产

- assets/template/report-template.md
- assets/indicator/core-indicator-dict.md
- skills/visual/*

## 输出结果

- HTML仪表盘
- 图表配置文件
- 数据文件
